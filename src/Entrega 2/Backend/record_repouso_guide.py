import os
import sys
import time
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPOUSO_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos", "repouso")
os.makedirs(REPOUSO_DIR, exist_ok=True)

SCENARIOS = [
    {
        "id": "01_estatico",
        "title": "1/5: Repouso Estatico (Bracos Soltos)",
        "desc": "Fique em pe, ereto, bracos relaxados ao lado do quadril, respirando naturalmente.",
        "duration": 15
    },
    {
        "id": "02_ready_position",
        "title": "2/5: Postura de Espera (Ready Position)",
        "desc": "Joelhos levemente flexionados, maos juntas na frente da cintura/peito, balanco suave.",
        "duration": 15
    },
    {
        "id": "03_caminhada",
        "title": "3/5: Caminhada e Deslocamento Suave",
        "desc": "De passos lentos para os lados, frente e tras, virando o corpo devagar.",
        "duration": 15
    },
    {
        "id": "04_angulos_distancias",
        "title": "4/5: Angulos e Distancias Diferentes",
        "desc": "Alterne entre ficar mais perto, mais longe e virado em 45 graus para os lados.",
        "duration": 15
    },
    {
        "id": "05_movimentos_casuais",
        "title": "5/5: Movimentos Casuais sem Golpe",
        "desc": "Ajeite a roupa, maos na cintura, respire fundo, sem fazer movimentos de swing.",
        "duration": 15
    }
]

def main():
    print("=" * 75)
    print(" TENNISSYNC - GRAVADOR GUIADO DE VIDEOS DE REPOUSO")
    print("=" * 75)
    print("Este assistente ira ajuda-lo a gravar 5 clipes de 15 segundos cada")
    print("para ensinar ao modelo a classe REPOUSO com maxima qualidade.")
    print(f"Destino dos videos: {REPOUSO_DIR}")
    print("=" * 75)

    cam_idx = 0
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        cam_idx = int(sys.argv[1])

    cap = cv2.VideoCapture(cam_idx)
    if not cap.isOpened():
        print(f"[ERRO] Nao foi possivel abrir a webcam indice {cam_idx}.")
        print("Tente passar o indice como argumento: py -3.11 record_repouso_guide.py 1")
        return

    # Tenta definir resolução 1280x720 ou mantém padrão da câmera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = 30.0

    print(f"\n[OK] Webcam detectada: {width}x{height} @ {fps:.1f} FPS")
    print("\nInstrucoes na janela de video:")
    print(" - [ESPACO]: Iniciar a gravacao do cenario atual (com 3s de contagem regressiva)")
    print(" - [P]: Pular cenario")
    print(" - [Q]: Sair do programa")
    print("=" * 75)

    scenario_idx = 0

    while scenario_idx < len(SCENARIOS):
        scenario = SCENARIOS[scenario_idx]
        title = scenario["title"]
        desc = scenario["desc"]
        duration = scenario["duration"]
        target_file = os.path.join(REPOUSO_DIR, f"repouso_{scenario['id']}.mp4")

        # Estado de espera (READY_TO_START)
        recording = False
        countdown = False
        start_time = 0.0
        countdown_start = 0.0
        recorded_frames = []

        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            display = frame.copy()
            now = time.time()

            # Desenha HUD com instruções
            # Faixa superior
            cv2.rectangle(display, (0, 0), (width, 85), (20, 20, 25), -1)
            cv2.putText(display, title, (20, 32), cv2.FONT_HERSHEY_DUPLEX, 0.85, (50, 220, 100), 2)
            cv2.putText(display, desc, (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1)

            # Faixa inferior de status
            cv2.rectangle(display, (0, height - 45), (width, height), (20, 20, 25), -1)

            if not countdown and not recording:
                cv2.putText(display, "Pressione [ESPACO] para iniciar contagem | [P] Pular | [Q] Sair",
                            (20, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 215, 255), 1)

            elif countdown:
                elapsed = now - countdown_start
                rem = 3 - int(elapsed)
                if rem > 0:
                    cv2.putText(display, f"POSICIONE-SE: {rem}...", (width // 2 - 180, height // 2),
                                cv2.FONT_HERSHEY_DUPLEX, 1.6, (0, 215, 255), 3)
                    cv2.putText(display, "Preparando gravacao...", (20, height - 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 215, 255), 1)
                else:
                    countdown = False
                    recording = True
                    start_time = time.time()
                    recorded_frames = []

            elif recording:
                recorded_frames.append(frame.copy())
                elapsed = now - start_time
                rem_rec = max(0.0, duration - elapsed)
                pct = min(1.0, elapsed / duration)

                # Borda vermelha piscante de gravação
                cv2.rectangle(display, (0, 0), (width - 1, height - 1), (0, 0, 255), 6)

                # Barra de progresso
                bar_w = int((width - 40) * pct)
                cv2.rectangle(display, (20, height - 35), (20 + bar_w, height - 15), (0, 0, 255), -1)
                cv2.putText(display, f"GRAVANDO: {rem_rec:4.1f}s restantes ({len(recorded_frames)} frames)",
                            (30, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

                if elapsed >= duration:
                    # Finalizar e salvar vídeo
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(target_file, fourcc, fps, (width, height))
                    for f in recorded_frames:
                        writer.write(f)
                    writer.release()
                    print(f"\n[SALVO COM SUCESSO] {target_file} ({len(recorded_frames)} frames)")
                    scenario_idx += 1
                    break

            cv2.imshow("TenniSync - Gravador de Repouso", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\nGravação cancelada pelo usuário.")
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key == ord('p') and not recording:
                print(f"\nCenário {scenario['id']} pulado.")
                scenario_idx += 1
                break
            elif key == 32 and not countdown and not recording:  # Espaço
                countdown = True
                countdown_start = time.time()

    cap.release()
    cv2.destroyAllWindows()
    print("\n" + "=" * 75)
    print(" TODOS OS CENARIOS FORAM PROCESSADOS!")
    print(f" Verifique os arquivos em: {REPOUSO_DIR}")
    print("=" * 75)

if __name__ == "__main__":
    main()
