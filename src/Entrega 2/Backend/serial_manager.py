import os
import sys
import time
import threading
from typing import Dict, List, Optional, Set, Union

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    serial = None
    HAS_SERIAL = False

try:
    from logger import log_info, log_warn, log_error
except ImportError:
    from Backend.logger import log_info, log_warn, log_error

JOINT_TO_BYTE = {
    'ombro_dir': 'A',
    'ombro_esq': 'B',
    'cotovelo_dir': 'C',
    'cotovelo_esq': 'D',
    'pulso_dir': 'E',
    'pulso_esq': 'F',
    'quadril_dir': 'G',
    'quadril_esq': 'H',
    'joelho_dir': 'I',
    'joelho_esq': 'J',
    'tornozelo_dir': 'K',
    'tornozelo_esq': 'L'
}

BYTE_TO_JOINT = {v: k for k, v in JOINT_TO_BYTE.items()}

class ArduinoController:
    """
    Gerenciador Serial Singleton Thread-Safe para o protótipo IoT do TenniSync.
    Controla 12 LEDs anatômicos (portas 2-13) e Buzzer (porta A0) do Arduino Uno.
    Suporta auto-detecção inteligente de porta COM, leitura assíncrona bidirecional,
    reconexão dinâmica e fallback transparente para simulação virtual.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ArduinoController, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, default_port: str = "COM4", baudrate: int = 9600):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self.default_port = default_port
        self.baudrate = baudrate
        self.active_port = None
        self.ser: Optional[serial.Serial] = None
        self.io_lock = threading.Lock()

        # Conjunto de LEDs acionados manualmente via site (bytes 'A'-'L')
        self.manual_leds: Set[str] = set()
        # Conjunto de LEDs acionados pelo motor de IA
        self.ai_leds: Set[str] = set()
        self.manual_override = False
        self.last_error: Optional[str] = None
        self.is_connected = False
        self._sweep_running = False

        # Timeout automático para apagar LEDs após tempo de exibição (segundos)
        self.auto_off_delay: float = 3.0
        self.last_led_time: float = 0.0

        # Logs e mensagens recebidas do Arduino
        self.recent_logs: List[Dict[str, Union[str, float]]] = []
        self._reader_running = False
        self._reader_thread: Optional[threading.Thread] = None

        self._connect()

    def list_available_ports(self) -> List[Dict[str, Union[str, bool]]]:
        """Lista todas as portas COM do sistema filtrando e identificando dispositivos USB / Arduino."""
        if not HAS_SERIAL:
            return []

        results = []
        try:
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                desc = (p.description or "").strip()
                hwid = (p.hwid or "").strip()
                desc_lower = desc.lower()
                hwid_lower = hwid.lower()

                # Verifica se é porta Bluetooth virtual
                is_bt = any(b in desc_lower or b in hwid_lower for b in ["bthenum", "bluetooth", "rfcomm"])

                # Verifica se é Arduino ou USB-Serial
                is_arduino = any(k in desc_lower or k in hwid_lower for k in [
                    "arduino", "genuino", "ch340", "ch341", "ftdi", "ft232",
                    "cp210", "vid:pid=2341", "vid:pid=1a86", "vid:pid=0403",
                    "vid:pid=10c4", "vid_2341", "vid_1a86", "vid_0403", "vid_10c4",
                    "dispositivo serial usb", "usb serial", "usb-serial", "serial usb"
                ])

                results.append({
                    "port": p.device,
                    "description": desc,
                    "hwid": hwid,
                    "is_bluetooth": is_bt,
                    "is_arduino_candidate": is_arduino and not is_bt,
                    "is_current": (p.device == self.active_port and self.is_connected)
                })
        except Exception as e:
            log_warn("IOT/SERIAL", f"Erro ao listar portas seriais: {e}")

        return results

    def _auto_detect_port(self) -> Optional[str]:
        """Auto-detecta a porta serial do Arduino com filtro para portas Bluetooth virtuais."""
        if not HAS_SERIAL:
            return None

        ports_info = self.list_available_ports()

        # 1. Candidatos explícitos a Arduino / USB-Serial que NÃO sejam Bluetooth
        candidates = [p["port"] for p in ports_info if p["is_arduino_candidate"]]
        if candidates:
            for c in candidates:
                if str(c).upper() == self.default_port.upper():
                    return str(c)
            return str(candidates[0])

        # 2. Portas não-Bluetooth gerais (ex: portas COM físicas ou adaptadores sem identificação explícita)
        non_bt = [p["port"] for p in ports_info if not p["is_bluetooth"]]
        if non_bt:
            for nb in non_bt:
                if str(nb).upper() == self.default_port.upper():
                    return str(nb)
            return str(non_bt[0])

        # 3. Se houver a porta padrão listada no sistema
        for p in ports_info:
            if str(p["port"]).upper() == self.default_port.upper():
                return str(p["port"])

        return None

    def _start_reader_thread(self):
        """Inicia thread de leitura em background para capturar logs e retornos do Arduino e watchdog de auto-off."""
        self._reader_running = True

        def _reader_loop():
            while self._reader_running and self.is_connected:
                try:
                    # Watchdog de Auto-Off: apaga LEDs automaticamente se o tempo expirar
                    if (self.ai_leds or (self.manual_override and self.manual_leds)) and self.auto_off_delay > 0:
                        if self.last_led_time > 0 and (time.time() - self.last_led_time) >= self.auto_off_delay:
                            with self.io_lock:
                                self._write_raw(b'R')
                                self.ai_leds.clear()
                                self.manual_leds.clear()
                                self.manual_override = False
                                self.last_led_time = 0.0
                                log_info("IOT/SERIAL", f"LEDs apagados automaticamente após timeout de {self.auto_off_delay:.1f}s.")

                    ser = self.ser
                    if not ser or not getattr(ser, "is_open", False):
                        break
                    if ser.in_waiting > 0:
                        line = ser.readline()
                        if line:
                            decoded = line.decode("utf-8", errors="replace").strip()
                            if decoded:
                                log_info("IOT/ARDUINO", f"Arduino -> {decoded}")
                                with self.io_lock:
                                    self.recent_logs.append({
                                        "time": time.strftime("%H:%M:%S"),
                                        "message": decoded
                                    })
                                    if len(self.recent_logs) > 30:
                                        self.recent_logs.pop(0)
                    else:
                        time.sleep(0.05)
                except Exception:
                    if not self._reader_running:
                        break
                    time.sleep(0.1)

        self._reader_thread = threading.Thread(target=_reader_loop, daemon=True)
        self._reader_thread.start()

    def connect(self, port: Optional[str] = None, baudrate: Optional[int] = None) -> Dict:
        """Conecta ou reconecta dinamicamente ao Arduino em uma porta específica ou automática."""
        if baudrate:
            self.baudrate = baudrate

        target_port = port if (port and port.upper() != "AUTO") else self._auto_detect_port() or self.default_port
        return self._connect(target_port)

    def _connect(self, port_to_try: Optional[str] = None) -> Dict:
        if not HAS_SERIAL:
            self.last_error = "Módulo pyserial não instalado."
            self.is_connected = False
            return self.get_status()

        with self.io_lock:
            self._reader_running = False
            if self.ser:
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None

            if not port_to_try:
                port_to_try = self._auto_detect_port() or self.default_port

            try:
                self.ser = serial.Serial(port=port_to_try, baudrate=self.baudrate, timeout=0.2)
                self.active_port = port_to_try
                self.is_connected = True
                self.last_error = None
                log_info("IOT/SERIAL", f"Arduino conectado com sucesso na porta {port_to_try} @ {self.baudrate} baud.")

                self._start_reader_thread()

                def _initial_sync():
                    time.sleep(1.2)
                    self._write_raw(b'R')

                threading.Thread(target=_initial_sync, daemon=True).start()

            except Exception as e:
                self.ser = None
                self.is_connected = False
                self.last_error = str(e)
                log_warn("IOT/SERIAL", f"Arduino offline na porta {port_to_try}: {e}. Operando em modo de simulação virtual.")

        return self.get_status()

    def _write_raw(self, data: bytes) -> bool:
        if not self.ser or not self.is_connected:
            return False
        try:
            self.ser.write(data)
            self.ser.flush()
            if data != b'R':
                self.last_led_time = time.time()
            return True
        except Exception as e:
            self.is_connected = False
            self.last_error = str(e)
            log_error("IOT/SERIAL", f"Falha na comunicação com o Arduino: {e}")
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            return False

    def write(self, data: Union[bytes, str]) -> int:
        """Compatibilidade duck-typing com serial.Serial.write()."""
        if isinstance(data, str):
            data = data.encode("ascii")
        with self.io_lock:
            success = self._write_raw(data)
            return len(data) if success else 0

    def flush(self):
        """Compatibilidade duck-typing com serial.Serial.flush()."""
        with self.io_lock:
            if self.ser and self.is_connected:
                try:
                    self.ser.flush()
                except Exception:
                    pass

    @property
    def is_open(self) -> bool:
        """Compatibilidade duck-typing com serial.Serial.is_open."""
        return self.is_connected and (self.ser is not None) and getattr(self.ser, "is_open", False)

    def send_byte(self, byte_char: str) -> bool:
        """Envia um byte de comando bruto ('A'-'L', 'a'-'l', 'R', ou '?')."""
        with self.io_lock:
            b = byte_char.encode("ascii")
            return self._write_raw(b)

    def ping(self) -> Dict:
        """Envia comando de verificação '?' para o Arduino e aguarda eco."""
        sent = self.send_byte('?')
        return {
            "status": "ok" if sent else "simulated",
            "sent": sent,
            "port": self.active_port or self.default_port,
            "is_connected": self.is_connected
        }

    def trigger_led(self, joint_or_byte: str, state: bool) -> Dict:
        """
        Liga ou desliga um LED específico a partir do site.
        Trata desligamento individual sem depender de firmware customizado.
        """
        byte_char = joint_or_byte.upper()
        if joint_or_byte in JOINT_TO_BYTE:
            byte_char = JOINT_TO_BYTE[joint_or_byte]

        if byte_char not in BYTE_TO_JOINT:
            return {"status": "error", "message": f"LED inválido: {joint_or_byte}"}

        with self.io_lock:
            self.manual_override = True

            if state:
                self.manual_leds.add(byte_char)
                self.last_led_time = time.time()
                # Envia byte maiúsculo para acender o LED e soar o buzzer
                self._write_raw(byte_char.encode("ascii"))
            else:
                if byte_char in self.manual_leds:
                    self.manual_leds.remove(byte_char)

                # Desliga: envia comando minúsculo 'a'-'l' e também reseta e resincroniza caso necessário
                self._write_raw(byte_char.lower().encode("ascii"))
                if not self.manual_leds:
                    self._write_raw(b'R')
                else:
                    self._write_raw(b'R')
                    for b in self.manual_leds:
                        self._write_raw(b.encode("ascii"))

        log_info("IOT/SERIAL", f"Controle manual de LED: {byte_char} ({BYTE_TO_JOINT.get(byte_char)}) -> {state}")
        return self.get_status()

    def toggle_led(self, joint_or_byte: str) -> Dict:
        byte_char = joint_or_byte.upper()
        if joint_or_byte in JOINT_TO_BYTE:
            byte_char = JOINT_TO_BYTE[joint_or_byte]

        current_state = byte_char in self.manual_leds
        return self.trigger_led(byte_char, not current_state)

    def trigger_side(self, side: str, state: bool = True) -> Dict:
        """
        Aciona ou apaga todos os 6 LEDs de um lado corporal específico ('left' ou 'right').
        'left' -> B (ombro_esq), D (cotovelo_esq), F (pulso_esq), H (quadril_esq), J (joelho_esq), L (tornozelo_esq)
        'right' -> A (ombro_dir), C (cotovelo_dir), E (pulso_dir), G (quadril_dir), I (joelho_dir), K (tornozelo_dir)
        """
        target_bytes = ['B', 'D', 'F', 'H', 'J', 'L'] if side.lower() in ['left', 'esq', 'esquerdo'] else ['A', 'C', 'E', 'G', 'I', 'K']
        with self.io_lock:
            self.manual_override = True
            if state:
                for b in target_bytes:
                    self.manual_leds.add(b)
                    self._write_raw(b.encode("ascii"))
                    time.sleep(0.01)
                self.last_led_time = time.time()
            else:
                for b in target_bytes:
                    if b in self.manual_leds:
                        self.manual_leds.remove(b)
                self._write_raw(b'R')
                for b in self.manual_leds:
                    self._write_raw(b.encode("ascii"))

        log_info("IOT/SERIAL", f"Controle manual por lado: {side} -> {state} ({target_bytes})")
        return self.get_status()

    def reset_all_leds(self) -> Dict:
        """Apaga todos os LEDs e retorna o controle para o modo automático da IA."""
        with self.io_lock:
            self.manual_leds.clear()
            self.ai_leds.clear()
            self.manual_override = False
            self.last_led_time = 0.0
            self._write_raw(b'R')
        log_info("IOT/SERIAL", "Todos os LEDs apagados e controle devolvido ao modo automático.")
        return self.get_status()

    def run_sweep_test(self):
        """Executa teste de bancada varrendo os 12 LEDs sequencialmente."""
        if self._sweep_running:
            return {"status": "busy", "message": "Varredura já em andamento"}

        def _sweep_thread():
            self._sweep_running = True
            log_info("IOT/SERIAL", "Iniciando teste de bancada: Varredura dos 12 LEDs...")
            try:
                self.reset_all_leds()
                time.sleep(0.1)
                for char in "ABCDEFGHIJKL":
                    with self.io_lock:
                        self.manual_leds = {char}
                        self.manual_override = True
                        self._write_raw(char.encode("ascii"))
                    time.sleep(0.18)
                with self.io_lock:
                    self._write_raw(b'R')
                    self.manual_leds.clear()
                    self.manual_override = False
                log_info("IOT/SERIAL", "Varredura dos 12 LEDs concluída com sucesso.")
            except Exception as e:
                log_error("IOT/SERIAL", f"Erro na varredura: {e}")
            finally:
                self._sweep_running = False

        t = threading.Thread(target=_sweep_thread, daemon=True)
        t.start()
        return {"status": "started", "message": "Varredura iniciada nos 12 LEDs"}

    def update_from_ai(self, failed_joints: List[str]):
        """
        Atualiza os LEDs físicos com base nas articulações reprovadas pela IA.
        Respeita o modo de override manual do usuário.
        """
        if self.manual_override and len(self.manual_leds) > 0:
            return

        with self.io_lock:
            if not failed_joints:
                if self.ai_leds:
                    self._write_raw(b'R')
                    self.ai_leds.clear()
                    self.last_led_time = 0.0
                return

            new_bytes = {JOINT_TO_BYTE[j] for j in failed_joints if j in JOINT_TO_BYTE}
            if new_bytes != self.ai_leds:
                for b in new_bytes:
                    self._write_raw(b.encode("ascii"))
                self.ai_leds = new_bytes
                self.last_led_time = time.time()

    def get_status(self) -> Dict:
        active_list = list(self.manual_leds | self.ai_leds)
        active_joints = [BYTE_TO_JOINT[b] for b in active_list if b in BYTE_TO_JOINT]
        return {
            "is_connected": self.is_connected,
            "port": self.active_port or self.default_port,
            "baudrate": self.baudrate,
            "manual_override": self.manual_override,
            "active_bytes": active_list,
            "active_joints": active_joints,
            "active_leds": active_joints,
            "is_sweep_running": self._sweep_running,
            "last_error": self.last_error,
            "available_ports": self.list_available_ports(),
            "recent_messages": list(self.recent_logs)
        }

    def close(self):
        self._reader_running = False
        with self.io_lock:
            if self.ser:
                try:
                    self.ser.write(b'R')
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                self.is_connected = False

# Instância Singleton Global
arduino_controller = ArduinoController()
