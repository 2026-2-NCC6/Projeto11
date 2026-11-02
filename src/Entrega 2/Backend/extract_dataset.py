import os
import sys
import glob
import argparse
import numpy as np
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pose_estimation import process_landmarks_to_tensor
from models.tennis_transformer import CLASS_MAP

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm", ".MP4", ".MOV", ".AVI")


def smooth_sequence(seq: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """
    Aplica filtro de média móvel simples ao longo do eixo temporal (Frames)
    para reduzir jittering do MediaPipe mantendo a borda intacta.
    seq shape: (N, 33, 3)
    """
    if kernel_size <= 1 or len(seq) < kernel_size:
        return seq
    smoothed = np.copy(seq)
    half = kernel_size // 2
    for t in range(len(seq)):
        start = max(0, t - half)
        end = min(len(seq), t + half + 1)
        smoothed[t] = np.mean(seq[start:end], axis=0)
    return smoothed


def mirror_landmarks_x(window: np.ndarray) -> np.ndarray:
    """
    Data Augmentation biomecânico: espelha horizontalmente o eixo X e troca os pares de
    landmarks esquerdos e direitos do MediaPipe Pose para dobrar o dataset ou simular canhoto/destro.
    window shape: (60, 33, 3)
    """
    mirrored = np.copy(window)
    mirrored[:, :, 0] = -mirrored[:, :, 0]

    # Pares simétricos do MediaPipe Pose (esquerdo <-> direito)
    symmetric_pairs = [
        (1, 4), (2, 5), (3, 6), (7, 8), (9, 10),
        (11, 12), (13, 14), (15, 16), (17, 18), (19, 20), (21, 22),
        (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)
    ]
    for left_idx, right_idx in symmetric_pairs:
        mirrored[:, [left_idx, right_idx], :] = mirrored[:, [right_idx, left_idx], :]

    return mirrored


def extract_landmarks_from_video(video_path: str, landmarker, cache_dir: str = None, class_name: str = "") -> np.ndarray:
    """
    Lê um arquivo de vídeo e retorna um array (NumFramesValidos, 33, 3)
    com os landmarks centralizados no quadril. Utiliza cache em disco e redimensionamento
    rápido para 640px (aumentando a velocidade do MediaPipe em até 5x na CPU).
    """
    vname = os.path.basename(video_path)
    cache_path = None
    if cache_dir:
        cache_path = os.path.join(cache_dir, f"{class_name}_{vname}.npy")
        if os.path.exists(cache_path):
            try:
                cached_data = np.load(cache_path)
                print(f"      [CACHE HIT] {vname}: Carregado do cache ({len(cached_data)} frames)", flush=True)
                return cached_data
            except Exception:
                pass

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  [ERRO] Não foi possível abrir o vídeo: {video_path}", flush=True)
        return np.empty((0, 33, 3), dtype=np.float32)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    frames_coords = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % 75 == 0 or frame_idx == total_frames:
            pct = int((frame_idx / total_frames) * 100)
            print(f"\r      Processando {vname} [{frame_idx}/{total_frames}] {pct}%...", end="", flush=True)

        # Otimização: MediaPipe Pose roda internamente em 256x256. Redimensionar de 1080p
        # para 640px economiza 9x de overhead de memória e acelera drasticamente a inferência.
        h, w = frame.shape[:2]
        if w > 640:
            new_w = 640
            new_h = int(h * (640 / w))
            proc_frame = cv2.resize(frame, (new_w, new_h))
        else:
            proc_frame = frame

        rgb_image = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        detection_result = landmarker.detect(mp_image)

        if detection_result.pose_landmarks:
            landmarks = detection_result.pose_landmarks[0]
            centered_coords = process_landmarks_to_tensor(landmarks)
            frames_coords.append(centered_coords)
        elif len(frames_coords) > 0:
            frames_coords.append(frames_coords[-1].copy())

    cap.release()
    print("", flush=True)  # quebra de linha após o \r

    if len(frames_coords) == 0:
        return np.empty((0, 33, 3), dtype=np.float32)

    result_arr = np.stack(frames_coords, axis=0)
    if cache_path:
        os.makedirs(cache_dir, exist_ok=True)
        try:
            np.save(cache_path, result_arr)
        except Exception:
            pass

    return result_arr



def slice_into_windows(sequence: np.ndarray, window_size: int = 60, stride: int = 15) -> list:
    """
    Corta uma sequência (N, 33, 3) em janelas de tamanho fixo (window_size, 33, 3).
    Se o vídeo tiver entre 30 e 59 frames válidos, faz interpolação temporal para 60 frames.
    """
    num_frames = len(sequence)
    if num_frames == 0:
        return []

    # Caso o vídeo seja um clipe curto do golpe (ex: 30 a 59 frames), reamostra para 60 frames
    if 30 <= num_frames < window_size:
        indices = np.linspace(0, num_frames - 1, window_size)
        resampled = np.zeros((window_size, 33, 3), dtype=np.float32)
        for lm in range(33):
            for c in range(3):
                resampled[:, lm, c] = np.interp(indices, np.arange(num_frames), sequence[:, lm, c])
        return [resampled]

    if num_frames < 30:
        return []

    windows = []
    for start in range(0, num_frames - window_size + 1, stride):
        windows.append(sequence[start:start + window_size])

    # Garante que o final do vídeo também seja incluído se sobrarem frames suficientes
    if (num_frames - window_size) % stride != 0:
        windows.append(sequence[num_frames - window_size:num_frames])

    return windows


def main():
    parser = argparse.ArgumentParser(description="Extrai landmarks 3D dos vídeos de tênis para treinar o TennisTransformerGPU.")
    parser.add_argument("--raw-dir", type=str, default=os.path.join(BASE_DIR, "dataset", "raw_videos"),
                        help="Diretório raiz contendo as pastas forehand, backhand, saque e repouso.")
    parser.add_argument("--out-file", type=str, default=os.path.join(BASE_DIR, "dataset", "processed", "tennis_dataset.npz"),
                        help="Caminho do arquivo .npz de saída.")
    parser.add_argument("--window-size", type=int, default=60, help="Tamanho da janela temporal (padrão: 60 frames).")
    parser.add_argument("--stride", type=int, default=10, help="Passo da janela deslizante entre amostras (padrão: 10 frames).")
    parser.add_argument("--smooth", type=int, default=3, help="Tamanho da janela de suavização temporal (0 ou 1 desativa).")
    parser.add_argument("--augment-mirror", action="store_true",
                        help="Gera cópias espelhadas horizontalmente (simula destro + canhoto).")
    args = parser.parse_args()

    model_path = os.path.join(BASE_DIR, "pose_landmarker_lite.task")
    if not os.path.exists(model_path):
        print(f"[ERRO] Modelo MediaPipe não encontrado em: {model_path}")
        sys.exit(1)

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    X_list = []
    y_list = []
    video_sources = []

    print("=" * 65)
    print(" TENNISSYNC - EXTRAÇÃO DE DATASET DE VÍDEOS (MEDIAPIPE 3D)")
    print("=" * 65)

    total_videos = 0
    for class_name, class_id in CLASS_MAP.items():
        class_dir = os.path.join(args.raw_dir, class_name)
        if not os.path.exists(class_dir):
            print(f"[AVISO] Pasta não encontrada: {class_dir}")
            continue

        video_files = [
            os.path.join(class_dir, f)
            for f in sorted(os.listdir(class_dir))
            if f.endswith(VIDEO_EXTENSIONS)
        ]

        print(f"\n-> Classe '{class_name.upper()}' (ID {class_id}): {len(video_files)} vídeo(s) encontrado(s)")
        class_windows = 0

        cache_dir = os.path.join(BASE_DIR, "dataset", "processed", "cache")
        for idx_v, vpath in enumerate(video_files, 1):
            total_videos += 1
            vname = os.path.basename(vpath)
            print(f"   [{idx_v:02d}/{len(video_files):02d}] {vname}", flush=True)
            seq = extract_landmarks_from_video(vpath, landmarker, cache_dir=cache_dir, class_name=class_name)

            if len(seq) < 30:
                print(f"   [IGNORADO] {vname}: apenas {len(seq)} frames com pose detectada (mínimo 30).", flush=True)
                continue

            if args.smooth > 1:
                seq = smooth_sequence(seq, kernel_size=args.smooth)

            windows = slice_into_windows(seq, window_size=args.window_size, stride=args.stride)
            for w in windows:
                X_list.append(w)
                y_list.append(class_id)
                video_sources.append(f"{class_name}/{vname}")
                class_windows += 1

                if args.augment_mirror:
                    X_list.append(mirror_landmarks_x(w))
                    y_list.append(class_id)
                    video_sources.append(f"{class_name}/{vname}#mirror")
                    class_windows += 1

            print(f"   [OK] {vname}: {len(seq)} frames -> {len(windows)} janela(s) extraída(s)", flush=True)

        print(f"   Total de amostras para '{class_name}': {class_windows}\n", flush=True)

    # Se a pasta 'repouso' estiver sem vídeos, gera amostras sintéticas de espera/postura neutra
    # baseadas nos frames iniciais dos vídeos reais para viabilizar o treinamento das 4 classes
    repouso_id = CLASS_MAP.get("repouso", 3)
    repouso_count = sum(1 for label in y_list if label == repouso_id)

    if repouso_count == 0 and len(X_list) > 0:
        print("\n" + "-" * 65)
        print("[INFO] Nenhum vídeo encontrado em 'repouso'.")
        print("       Gerando amostras sintéticas de repouso (posição base neutra/espera)")
        print("       a partir das posturas iniciais para permitir o treinamento das 4 classes...")
        print("-" * 65)

        # Coleta poses iniciais (primeiro frame de várias janelas reais)
        ref_indices = np.linspace(0, len(X_list) - 1, min(20, len(X_list)), dtype=int)
        rng = np.random.default_rng(42)

        for i, ref_idx in enumerate(ref_indices):
            base_pose = X_list[ref_idx][0].copy()  # (33, 3)

            # Gera 2 variações temporais de postura de espera para cada base
            for v in range(2):
                repouso_window = np.zeros((args.window_size, 33, 3), dtype=np.float32)
                # Oscilação sutil natural de espera/split-step (senoidal + ruído)
                freq = rng.uniform(0.5, 1.5)
                phase = rng.uniform(0, 2 * np.pi)
                amp = rng.uniform(0.005, 0.015)

                for t in range(args.window_size):
                    sway = np.sin(2 * np.pi * freq * (t / args.window_size) + phase) * amp
                    noise = rng.normal(0, 0.003, size=(33, 3)).astype(np.float32)
                    frame_pose = base_pose.copy()
                    frame_pose[:, 1] += sway  # leve oscilação vertical no quadril/tronco
                    frame_pose[:, 0] += sway * 0.5  # leve oscilação lateral
                    repouso_window[t] = frame_pose + noise

                X_list.append(repouso_window)
                y_list.append(repouso_id)
                video_sources.append(f"repouso/synthetic_neutral_{i}_{v}")

        print(f"   [OK] Amostras de repouso geradas: {sum(1 for label in y_list if label == repouso_id)} janelas")

    if len(X_list) == 0:
        print("\n" + "!" * 65)
        print(" Nenhuma janela extraída! Adicione vídeos (.mp4, .mov, .avi) em:")
        for cname in CLASS_MAP:
            print(f"  - {os.path.join(args.raw_dir, cname)}")
        print("!" * 65)
        sys.exit(0)

    X = np.stack(X_list, axis=0).astype(np.float32)
    y = np.array(y_list, dtype=np.int64)
    sources = np.array(video_sources)

    os.makedirs(os.path.dirname(args.out_file), exist_ok=True)
    np.savez_compressed(args.out_file, X=X, y=y, sources=sources)

    print("\n" + "=" * 65)
    print(f" DATASET SALVO COM SUCESSO: {args.out_file}")
    print(f" Vídeos processados : {total_videos}")
    print(f" Formato de X       : {X.shape} (Amostras, Frames, Landmarks, Coords)")
    print(f" Formato de y       : {y.shape}")
    for cname, cid in CLASS_MAP.items():
        count = int(np.sum(y == cid))
        print(f"   - {cname.capitalize():10s} (ID {cid}): {count} amostras")
    print("=" * 65)


if __name__ == "__main__":
    main()
