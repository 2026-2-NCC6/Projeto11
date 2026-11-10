from camera_utils import get_usb_camera_source, is_camera_blacklisted
import os
import sys
import time
import argparse
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.tennis_transformer import CLASS_MAP


def main():
    parser = argparse.ArgumentParser(description="Gravador interativo de vídeos de treinamento para o TennisSync.")
    parser.add_argument("--camera", type=int, default=0, help="Índice da webcam (padrão: 0, tente 1 se usar câmera externa).")
    parser.add_argument("--duration", type=float, default=2.5, help="Duração de cada clipe gravado em segundos (padrão: 2.5s).")
    parser.add_argument("--fps", type=int, default=30, help="FPS de gravação (padrão: 30 FPS).")
    parser.add_argument("--countdown", type=int, default=3, help="Contagem regressiva antes de gravar (padrão: 3s).")
    args = parser.parse_args()

    raw_dir = os.path.join(BASE_DIR, "dataset", "raw_videos")
    for cname in CLASS_MAP:
        os.makedirs(os.path.join(raw_dir, cname), exist_ok=True)

    model_path = os.path.join(BASE_DIR, "pose_landmarker_lite.task")
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"[ERRO] Não foi possível abrir a câmera de índice {args.camera}. Tente --camera 1.")
        sys.exit(1)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

    key_to_class = {
        ord('1'): "forehand",
        ord('2'): "backhand",
        ord('3'): "saque",
        ord('4'): "repouso"
    }

    state = "IDLE"  # IDLE, COUNTDOWN, RECORDING
    target_class = None
    state_start_time = 0.0
    recorded_frames = []
    status_msg = "Pressione: [1] Forehand | [2] Backhand | [3] Saque | [4] Repouso | [Q] Sair"

    print("=" * 70)
    print(" GRAVADOR DE DATASET TENNISSYNC")
    print(" Controles na janela de vídeo:")
    print("   [1] Gravar FOREHAND")
    print("   [2] Gravar BACKHAND")
    print("   [3] Gravar SAQUE")
    print("   [4] Gravar REPOUSO")
    print("   [Q] Sair")
    print("=" * 70)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        detection_result = landmarker.detect(mp_image)

        annotated = np.copy(frame)
        has_pose = bool(detection_result.pose_landmarks)

        if has_pose:
            drawing_utils.draw_landmarks(
                image=annotated,
                landmark_list=detection_result.pose_landmarks[0],
                connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
                landmark_drawing_spec=drawing_styles.get_default_pose_landmarks_style()
            )

        now = time.time()

        if state == "COUNTDOWN":
            elapsed = now - state_start_time
            remaining = args.countdown - int(elapsed)
            if remaining > 0:
                cv2.putText(annotated, f"PREPARE-SE ({target_class.upper()}): {remaining}...",
                            (30, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 215, 255), 3)
            else:
                state = "RECORDING"
                state_start_time = now
                recorded_frames = []

        elif state == "RECORDING":
            recorded_frames.append(frame.copy())
            elapsed = now - state_start_time
            progress = min(1.0, elapsed / args.duration)

            # Borda vermelha indicando gravação ativa
            cv2.rectangle(annotated, (0, 0), (width - 1, height - 1), (0, 0, 255), 6)
            cv2.putText(annotated, f"GRAVANDO {target_class.upper()} ({len(recorded_frames)} frames)",
                        (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            if elapsed >= args.duration:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                out_path = os.path.join(raw_dir, target_class, f"{target_class}_{timestamp}.mp4")
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                writer = cv2.VideoWriter(out_path, fourcc, args.fps, (width, height))
                for f in recorded_frames:
                    writer.write(f)
                writer.release()

                print(f"[SALVO] {out_path} ({len(recorded_frames)} frames)")
                status_msg = f"Salvo: {os.path.basename(out_path)} ({len(recorded_frames)} frames)"
                state = "IDLE"

        # Barra de status no topo
        pose_color = (0, 255, 0) if has_pose else (0, 0, 255)
        pose_text = "Pose: OK" if has_pose else "Pose: NAO DETECTADA"
        cv2.putText(annotated, pose_text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, pose_color, 2)
        cv2.putText(annotated, status_msg, (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        cv2.imshow("TennisSync - Coleta de Videos", annotated)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif state == "IDLE" and key in key_to_class:
            target_class = key_to_class[key]
            state = "COUNTDOWN"
            state_start_time = time.time()

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


if __name__ == "__main__":
    main()
