from camera_utils import get_usb_camera_source, is_camera_blacklisted
import os
import sys
import time
import argparse
import cv2
import numpy as np

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPOUSO_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos", "repouso")
os.makedirs(REPOUSO_DIR, exist_ok=True)

def play_beep(freq, duration_ms):
    if HAS_SOUND:
        try:
            winsound.Beep(freq, duration_ms)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Grava um clipe único para o dataset.")
    parser.add_argument("--filename", type=str, required=True, help="Nome do arquivo de saída (ex: repouso_01_estatico.mp4)")
    parser.add_argument("--duration", type=float, default=15.0, help="Duração em segundos da gravação (padrão: 15s)")
    parser.add_argument("--countdown", type=int, default=5, help="Contagem regressiva em segundos para se posicionar (padrão: 5s)")
    parser.add_argument("--title", type=str, default="GRAVAÇÃO DE CLIPE", help="Título exibido na tela")
    parser.add_argument("--desc", type=str, default="", help="Descrição da postura")
    parser.add_argument("--camera", type=int, default=0, help="Índice da câmera (padrão: 0)")
    args = parser.parse_args()

    out_path = os.path.join(REPOUSO_DIR, args.filename)
    if not out_path.endswith(".mp4"):
        out_path += ".mp4"

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"[ERRO] Câmera {args.camera} não pôde ser aberta.")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = 30.0

    print(f"[INICIANDO] {args.title}")
    print(f"-> Contagem de {args.countdown} segundos para posicionamento...")

    # 1. Fase de Contagem Regressiva
    countdown_start = time.time()
    last_second = -1

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        elapsed = time.time() - countdown_start
        remaining = args.countdown - int(elapsed)

        if remaining != last_second and remaining > 0:
            last_second = remaining
            print(f" [PREPARE-SE] {remaining}...")
            play_beep(800, 150)

        display = frame.copy()

        # HUD superior
        cv2.rectangle(display, (0, 0), (width, 70), (25, 25, 30), -1)
        cv2.putText(display, args.title, (20, 30), cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 220, 120), 2)
        if args.desc:
            cv2.putText(display, args.desc, (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)

        # Contagem central
        if remaining > 0:
            cv2.putText(display, f"POSICIONE-SE: {remaining}s", (width // 2 - 190, height // 2),
                        cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 215, 255), 3)
        else:
            cv2.putText(display, "GRAVANDO AGORA!", (width // 2 - 170, height // 2),
                        cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 0, 255), 3)

        cv2.imshow("TenniSync - Gravador", display)
        cv2.waitKey(1)

        if elapsed >= args.countdown:
            break

    # Sinal de início de gravação
    print("\n[GRAVANDO AGORA!]")
    play_beep(1400, 350)

    # 2. Fase de Gravação
    recorded_frames = []
    rec_start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        recorded_frames.append(frame.copy())
        elapsed = time.time() - rec_start
        remaining = max(0.0, args.duration - elapsed)
        pct = min(1.0, elapsed / args.duration)

        display = frame.copy()

        # Borda vermelha de gravação
        cv2.rectangle(display, (0, 0), (width - 1, height - 1), (0, 0, 255), 5)

        # HUD superior
        cv2.rectangle(display, (0, 0), (width, 55), (25, 25, 30), -1)
        cv2.putText(display, f"REC: {args.title}", (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 0, 255), 2)

        # Barra de progresso inferior
        cv2.rectangle(display, (0, height - 40), (width, height), (25, 25, 30), -1)
        bar_w = int((width - 40) * pct)
        cv2.rectangle(display, (20, height - 30), (20 + bar_w, height - 12), (0, 0, 255), -1)
        cv2.putText(display, f"{remaining:4.1f}s restantes ({len(recorded_frames)} frames)",
                    (width - 240, height - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("TenniSync - Gravador", display)
        cv2.waitKey(1)

        if elapsed >= args.duration:
            break

    cap.release()
    cv2.destroyAllWindows()

    # 3. Salvar o arquivo de vídeo
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
    for f in recorded_frames:
        writer.write(f)
    writer.release()

    play_beep(1200, 150)
    play_beep(1600, 250)

    print(f"\n[SUCESSO] Vídeo salvo em: {out_path}")
    print(f"Total de frames: {len(recorded_frames)} ({len(recorded_frames)/fps:.1f}s)")

if __name__ == "__main__":
    main()
