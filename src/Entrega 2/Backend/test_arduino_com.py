"""
TenniSync - Utilitário de Teste e Diagnóstico de Comunicação Arduino <-> PC
Permite testar portas seriais, handshake, acionamento de LEDs e retorno de eco em tempo real.
"""

import sys
import time
import argparse

try:
    from serial_manager import arduino_controller, JOINT_TO_BYTE, BYTE_TO_JOINT
except ImportError:
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, BASE_DIR)
    from serial_manager import arduino_controller, JOINT_TO_BYTE, BYTE_TO_JOINT

def run_diagnostic(port=None):
    print("=" * 65)
    print("      TENNISSYNC - DIAGNÓSTICO DE COMUNICAÇÃO ARDUINO UNO")
    print("=" * 65)

    print("\n1. Detectando portas COM disponíveis no sistema...")
    ports = arduino_controller.list_available_ports()
    if not ports:
        print(" [!] Nenhuma porta COM detectada no sistema.")
    else:
        for p in ports:
            marker = " -> CANDIDATO ARDUINO" if p.get("is_arduino_candidate") else ""
            bt = " (Bluetooth)" if p.get("is_bluetooth") else ""
            print(f"    - {p['port']}: {p['description']}{bt}{marker}")

    print("\n2. Conectando ao Arduino...")
    target_port = port if port else "AUTO"
    status = arduino_controller.connect(port=target_port)
    print(f"    Porta: {status['port']} | Conectado: {status['is_connected']}")

    if not status["is_connected"]:
        print(f" [X] Falha ao abrir porta serial: {status.get('last_error')}")
        print("     Verifique se o cabo USB está conectado ou se outro programa está usando a porta.")
        return False

    print(" [OK] Porta Serial aberta com sucesso! Aguardando estabilização (1.5s)...")
    time.sleep(1.5)

    print("\n3. Enviando Handshake de Teste ('?')...")
    arduino_controller.send_byte('?')
    time.sleep(0.3)
    if arduino_controller.recent_logs:
        last_msg = arduino_controller.recent_logs[-1]["message"]
        print(f"    Eco recebido do Arduino: \"{last_msg}\"")
    else:
        print("    (Nenhuma resposta de texto imediata, prosseguindo com teste de atuadores)")

    print("\n4. Testando Acionamento Sequencial dos 12 LEDs Anatômicos:")
    for code in "ABCDEFGHIJKL":
        joint = BYTE_TO_JOINT.get(code, "desconhecido")
        print(f"    - Acendendo LED '{code}' ({joint})...", end="", flush=True)
        arduino_controller.trigger_led(code, True)
        time.sleep(0.2)
        if arduino_controller.recent_logs:
            last = arduino_controller.recent_logs[-1]["message"]
            print(f" Resposta: {last}")
        else:
            print(" Enviado.")

    print("\n5. Enviando Comando de Reset ('R')...")
    arduino_controller.reset_all_leds()
    time.sleep(0.3)
    if arduino_controller.recent_logs:
        print(f"    Resposta: {arduino_controller.recent_logs[-1]['message']}")

    print("\n" + "=" * 65)
    print(" [OK] DIAGNÓSTICO CONCLUÍDO COM SUCESSO! HARDWARE RESPONDENDO.")
    print("=" * 65)
    return True

def run_interactive():
    print("\n--- MODO INTERATIVO SERIAL ---")
    print("Digite 'A'-'L' para ligar/apagar LED, 'R' para apagar todos, '?' para ping, 'Q' para sair:")
    while True:
        try:
            cmd = input("Comando > ").strip().upper()
            if not cmd:
                continue
            if cmd == 'Q':
                break
            if cmd == 'R':
                arduino_controller.reset_all_leds()
                print("Todos apagados.")
            elif cmd == '?':
                arduino_controller.ping()
                time.sleep(0.2)
                if arduino_controller.recent_logs:
                    print(f"Arduino: {arduino_controller.recent_logs[-1]['message']}")
            elif len(cmd) == 1 and 'A' <= cmd <= 'L':
                res = arduino_controller.toggle_led(cmd)
                active = res.get("active_bytes", [])
                state = "LIGADO" if cmd in active else "APAGADO"
                print(f"LED {cmd} ({BYTE_TO_JOINT.get(cmd)}): {state}")
            else:
                print("Comando inválido. Use 'A'-'L', 'R', '?' ou 'Q'.")
        except (KeyboardInterrupt, EOFError):
            break

    arduino_controller.reset_all_leds()
    arduino_controller.close()
    print("\nSessão encerrada.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de Comunicação Serial Arduino <-> PC TenniSync")
    parser.add_argument("--port", type=str, default=None, help="Porta COM específica (ex: COM9, COM4). Padrão: auto-detecção")
    parser.add_argument("-i", "--interactive", action="store_true", help="Inicia modo interativo pelo terminal")
    args = parser.parse_args()

    success = run_diagnostic(port=args.port)
    if success and args.interactive:
        run_interactive()
    else:
        arduino_controller.close()
