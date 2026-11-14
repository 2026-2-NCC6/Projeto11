import os
import sys
import time
import threading
from typing import Dict, List, Optional, Set

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

        self._connect()

    def _auto_detect_port(self) -> Optional[str]:
        if not HAS_SERIAL:
            return None
        ports = list(serial.tools.list_ports.comports())
        # Tenta primeiro a porta padrão
        for p in ports:
            if p.device.upper() == self.default_port.upper():
                return p.device

        # Procura por palavras-chave de Arduino/CH340/FTDI/USB
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in ["arduino", "ch340", "ftdi", "usb serial", "usb-serial"]):
                return p.device

        # Se houver apenas uma porta COM no sistema, usa ela
        if len(ports) == 1:
            return ports[0].device

        return None

    def _connect(self):
        if not HAS_SERIAL:
            self.last_error = "Módulo pyserial não instalado."
            self.is_connected = False
            return

        with self.io_lock:
            port_to_try = self._auto_detect_port() or self.default_port
            try:
                # Evita resetar o Arduino Uno configurando dtr=None ou inicializando com timeout
                self.ser = serial.Serial(port=port_to_try, baudrate=self.baudrate, timeout=0.1)
                self.active_port = port_to_try
                self.is_connected = True
                self.last_error = None
                log_info("IOT/SERIAL", f"Arduino conectado com sucesso na porta {port_to_try} @ {self.baudrate} baud.")
            except Exception as e:
                self.ser = None
                self.is_connected = False
                self.last_error = str(e)
                log_warn("IOT/SERIAL", f"Arduino offline na porta {port_to_try}: {e}. Operando em modo de simulação virtual.")

    def _write_raw(self, data: bytes) -> bool:
        if not self.ser or not self.is_connected:
            return False
        try:
            self.ser.write(data)
            self.ser.flush()
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

    def send_byte(self, byte_char: str) -> bool:
        """Envia um byte de comando bruto ('A'-'L', 'a'-'l' ou 'R')."""
        with self.io_lock:
            b = byte_char.encode("ascii")
            return self._write_raw(b)

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
                    # Resincronização instantânea para firmwares que só conhecem 'R'
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

    def reset_all_leds(self) -> Dict:
        """Apaga todos os LEDs e retorna o controle para o modo automático da IA."""
        with self.io_lock:
            self.manual_leds.clear()
            self.ai_leds.clear()
            self.manual_override = False
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
        # Se o usuário está controlando manualmente, a IA não desliga os LEDs dele
        if self.manual_override and len(self.manual_leds) > 0:
            return

        with self.io_lock:
            if not failed_joints:
                if self.ai_leds:
                    self._write_raw(b'R')
                    self.ai_leds.clear()
                return

            new_bytes = {JOINT_TO_BYTE[j] for j in failed_joints if j in JOINT_TO_BYTE}
            if new_bytes != self.ai_leds:
                for b in new_bytes:
                    self._write_raw(b.encode("ascii"))
                self.ai_leds = new_bytes

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
            "last_error": self.last_error
        }

    def close(self):
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
