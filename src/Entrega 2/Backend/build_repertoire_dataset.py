import os
import sys
import glob
import time
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from pose_estimation import process_landmarks_to_tensor
from models.tennis_transformer import CLASS_MAP

RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos")
OUT_NPZ = os.path.join(BASE_DIR, "dataset", "processed", "tennis_dataset.npz")
CACHE_DIR = os.path.join(BASE_DIR, "dataset", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUT_NPZ), exist_ok=True)

def mirror_landmarks_x(window: np.ndarray) -> np.ndarray:
    """Espelha horizontalmente o eixo X e inverte pares anatômicos (canhoto/destro)."""
    mirrored = np.copy(window)
    mirrored[:, :, 0] = -mirrored[:, :, 0]
    symmetric_pairs = [
        (1, 4), (2, 5), (3, 6), (7, 8), (9, 10),
        (11, 12), (13, 14), (15, 16), (17, 18), (19, 20), (21, 22),
        (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)
    ]
    for left_idx, right_idx in symmetric_pairs:
        mirrored[:, [left_idx, right_idx], :] = mirrored[:, [right_idx, left_idx], :]
    return mirrored

def extract_landmarks_from_video(video_path: str, landmarker) -> np.ndarray:
    """Extrai landmarks centralizados no quadril com cache para aceleração."""
    vname = os.path.basename(video_path)
    cache_path = os.path.join(CACHE_DIR, f"{vname}.npy")
    if os.path.exists(cache_path):
        try:
            return np.load(cache_path)
        except Exception:
            pass

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return np.empty((0, 33, 3), dtype=np.float32)

    frames_coords = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        if w > 640:
            frame = cv2.resize(frame, (640, int(h * (640 / w))))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = landmarker.detect(mp_img)

        if res.pose_landmarks:
            coords = process_landmarks_to_tensor(res.pose_landmarks[0])
            frames_coords.append(coords)
        elif len(frames_coords) > 0:
            frames_coords.append(frames_coords[-1].copy())

    cap.release()
    if len(frames_coords) == 0:
        return np.empty((0, 33, 3), dtype=np.float32)

    arr = np.stack(frames_coords, axis=0)
    try:
        np.save(cache_path, arr)
    except Exception:
        pass
    return arr

def generate_synthetic_resting_windows(num_windows: int = 150) -> list:
    """
    Gera janelas ricas de repouso com atleta em posições variadas:
    1. Sentado à mesa/computador (mãos para frente digitando ou no colo).
    2. De pé com braços relaxados ao lado do quadril.
    3. De pé em postura de espera/ready stance.
    """
    rng = np.random.default_rng(2026)
    windows = []

    for w_idx in range(num_windows):
        pose = np.zeros((33, 3), dtype=np.float32)
        scale = rng.uniform(0.88, 1.12)

        # Cabeça e tronco
        pose[0] = [0.0, -0.40, -0.38]    # Nariz
        pose[11] = [0.07, -0.27, -0.16]  # Ombro esq
        pose[12] = [-0.07, -0.27, -0.16] # Ombro dir
        pose[23] = [0.035, 0.0, 0.0]     # Quadril esq
        pose[24] = [-0.035, 0.0, 0.0]    # Quadril dir

        style = w_idx % 4
        if style == 0:
            # 1. De pé: braços caídos relaxados
            pose[13] = [0.08, -0.10, -0.05]
            pose[14] = [-0.08, -0.10, -0.05]
            pose[15] = [0.08, 0.04, -0.10]
            pose[16] = [-0.08, 0.04, -0.10]
            # Pernas retas
            pose[25] = [0.04, 0.35, 0.0]; pose[26] = [-0.04, 0.35, 0.0]
            pose[27] = [0.04, 0.70, 0.0]; pose[28] = [-0.04, 0.70, 0.0]
        elif style == 1:
            # 2. Sentado à mesa: mãos à frente (digitando/repousando na mesa)
            pose[13] = [0.07, -0.12, 0.08]
            pose[14] = [-0.07, -0.12, 0.08]
            pose[15] = [0.04, -0.04, 0.22]
            pose[16] = [-0.04, -0.04, 0.22]
            # Pernas dobradas como sentado
            pose[25] = [0.05, 0.15, 0.30]; pose[26] = [-0.05, 0.15, 0.30]
            pose[27] = [0.05, 0.45, 0.30]; pose[28] = [-0.05, 0.45, 0.30]
        elif style == 2:
            # 3. Ready position de tênis (mãos juntas segurando o cabo da raquete na cintura)
            pose[13] = [0.08, -0.13, 0.12]
            pose[14] = [-0.08, -0.13, 0.12]
            pose[15] = [0.02, -0.02, 0.20]
            pose[16] = [-0.02, -0.02, 0.20]
            pose[25] = [0.05, 0.30, 0.05]; pose[26] = [-0.05, 0.30, 0.05]
            pose[27] = [0.05, 0.65, 0.0]; pose[28] = [-0.05, 0.65, 0.0]
        else:
            # 4. De pé casual: uma mão no bolso/cintura e outra relaxada
            pose[13] = [0.08, -0.10, -0.05]
            pose[14] = [-0.10, -0.12, 0.05]
            pose[15] = [0.08, 0.04, -0.10]
            pose[16] = [-0.06, -0.02, 0.02]
            pose[25] = [0.04, 0.35, 0.0]; pose[26] = [-0.04, 0.35, 0.0]
            pose[27] = [0.04, 0.70, 0.0]; pose[28] = [-0.04, 0.70, 0.0]

        # Normaliza escala para ombros ~0.40
        pose = pose * (0.40 / 0.14) * scale

        # Fixa os dedos nos pulsos
        for wrist_idx, finger_indices in [(15, [17, 19, 21]), (16, [18, 20, 22])]:
            pose[finger_indices] = pose[wrist_idx]

        seq = np.zeros((60, 33, 3), dtype=np.float32)
        breath_freq = rng.uniform(0.15, 0.30)
        sway_freq = rng.uniform(0.05, 0.15)

        for t in range(60):
            breath = 0.005 * np.sin(2 * np.pi * breath_freq * (t / 30.0))
            sway = 0.006 * np.sin(2 * np.pi * sway_freq * (t / 30.0))
            frame_pose = pose.copy()
            frame_pose[:, 0] += sway
            frame_pose[[0, 11, 12, 13, 14], 1] += breath
            noise = rng.normal(0, 0.003, size=(33, 3)).astype(np.float32)
            seq[t] = frame_pose + noise

        windows.append(seq)

    return windows

def main():
    print("=" * 70)
    print(" TENNISSYNC: COMPILAÇÃO DO DATASET EQUILIBRADO (4 PASTAS OFICIAIS)")
    print(" (Forehand, Backhand, Saque e Repouso - THETIS + Gravações Reais do Atleta)")
    print("=" * 70)

    model_path = os.path.join(BASE_DIR, "pose_landmarker_full.task")
    if not os.path.exists(model_path):
        model_path = os.path.join(BASE_DIR, "pose_landmarker_lite.task")
    print(f"-> Usando MediaPipe Pose Model: {os.path.basename(model_path)}")
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.IMAGE)
    landmarker = vision.PoseLandmarker.create_from_options(options)

    X_list = []
    y_list = []
    sources_list = []
    extracted_counts = {c: 0 for c in CLASS_MAP}
    repouso_id = CLASS_MAP["repouso"]

    # 1. Processar as 3 Classes de Golpes (Forehand, Backhand, Saque)
    stroke_classes = ["forehand", "backhand", "saque"]

    for stroke_name in stroke_classes:
        class_id = CLASS_MAP[stroke_name]
        v_files = sorted(glob.glob(os.path.join(RAW_DIR, stroke_name, "*.avi")) + \
                         glob.glob(os.path.join(RAW_DIR, stroke_name, "*.mp4")))
        
        user_vids = [f for f in v_files if os.path.basename(f).startswith("user_")]
        thetis_vids = [f for f in v_files if not os.path.basename(f).startswith("user_")]

        print(f"\n-> Processando {len(v_files)} vídeos de {stroke_name.upper()} ({len(thetis_vids)} THETIS + {len(user_vids)} do Atleta)...")

        # 1.1 Processar vídeos THETIS
        for v_path in thetis_vids:
            v_base = os.path.basename(v_path)
            seq = extract_landmarks_from_video(v_path, landmarker)
            if len(seq) < 30:
                continue

            if len(seq) < 60:
                indices = np.linspace(0, len(seq) - 1, 60)
                resampled = np.zeros((60, 33, 3), dtype=np.float32)
                for lm in range(33):
                    for c in range(3):
                        resampled[:, lm, c] = np.interp(indices, np.arange(len(seq)), seq[:, lm, c])
                windows = [resampled]
            else:
                windows = [seq[s:s+60] for s in range(0, len(seq) - 60 + 1, 6)]

            for w in windows:
                wm_t = (np.std(w[:, 15, :2], axis=0).mean() + np.std(w[:, 16, :2], axis=0).mean()) / 2.0
                disp_t = max(np.ptp(w[:, 15, :2], axis=0).max(), np.ptp(w[:, 16, :2], axis=0).max())
                em_t = (np.std(w[:, 13, :2], axis=0).mean() + np.std(w[:, 14, :2], axis=0).mean()) / 2.0

                if (wm_t >= 0.065 and disp_t >= 0.28) or em_t >= 0.045:
                    X_list.append(w)
                    y_list.append(class_id)
                    sources_list.append(f"{stroke_name}/{v_base}")

                    w_mir = mirror_landmarks_x(w)
                    X_list.append(w_mir)
                    y_list.append(class_id)
                    sources_list.append(f"{stroke_name}/{v_base}#mirror")
                    extracted_counts[stroke_name] += 2
                elif wm_t < 0.025 and disp_t < 0.15 and em_t < 0.020:
                    X_list.append(w)
                    y_list.append(repouso_id)
                    sources_list.append(f"thetis_idle/{v_base}")
                    extracted_counts["repouso"] += 1

        # 1.2 Processar vídeos reais gravados pelo Atleta ao fundo (forehand, backhand, saque)
        for v_path in user_vids:
            v_base = os.path.basename(v_path)
            seq = extract_landmarks_from_video(v_path, landmarker)
            if len(seq) < 30:
                continue

            if len(seq) < 60:
                indices = np.linspace(0, len(seq) - 1, 60)
                resampled = np.zeros((60, 33, 3), dtype=np.float32)
                for lm in range(33):
                    for c in range(3):
                        resampled[:, lm, c] = np.interp(indices, np.arange(len(seq)), seq[:, lm, c])
                windows = [resampled]
            else:
                # Amostragem densa (step=3) para aproveitar toda a dinâmica dos golpes do usuário
                windows = [seq[s:s+60] for s in range(0, len(seq) - 60 + 1, 3)]

            for w in windows:
                wm_max = max(np.std(w[:, 15, :2], axis=0).mean(), np.std(w[:, 16, :2], axis=0).mean())
                disp_max = max(np.ptp(w[:, 15, :2], axis=0).max(), np.ptp(w[:, 16, :2], axis=0).max())
                em_max = max(np.std(w[:, 13, :2], axis=0).mean(), np.std(w[:, 14, :2], axis=0).mean())

                # Portão unilateral para os golpes reais do usuário
                if (wm_max >= 0.035 and disp_max >= 0.18) or (em_max >= 0.030 and disp_max >= 0.16):
                    X_list.append(w)
                    y_list.append(class_id)
                    sources_list.append(f"{stroke_name}_user/{v_base}")

                    w_mir = mirror_landmarks_x(w)
                    X_list.append(w_mir)
                    y_list.append(class_id)
                    sources_list.append(f"{stroke_name}_user/{v_base}#mirror")
                    extracted_counts[stroke_name] += 2

    # 2. Processar a Pasta Oficial de REPOUSO (55 vídeos reais do atleta)
    rep_files = sorted(glob.glob(os.path.join(RAW_DIR, "repouso", "*.mp4")) + \
                       glob.glob(os.path.join(RAW_DIR, "repouso", "*.avi")))
    print(f"\n-> Processando {len(rep_files)} vídeos reais de REPOUSO gravados pelo atleta...")
    for v_path in rep_files:
        v_base = os.path.basename(v_path)
        seq = extract_landmarks_from_video(v_path, landmarker)
        if len(seq) >= 60:
            # Step=8 para balancear perfeitamente com a quantidade de golpes
            for s in range(0, len(seq) - 60 + 1, 8):
                w = seq[s:s+60]
                X_list.append(w)
                y_list.append(repouso_id)
                sources_list.append(f"repouso/{v_base}")

                w_mir = mirror_landmarks_x(w)
                X_list.append(w_mir)
                y_list.append(repouso_id)
                sources_list.append(f"repouso/{v_base}#mirror")
                extracted_counts["repouso"] += 2

    # 3. Adicionar Janelas Sintéticas de Repouso (posturas estáticas ancoradas)
    print("\n-> Adicionando posturas de repouso estático ancoradas...")
    synth_windows = generate_synthetic_resting_windows(num_windows=100)
    for i, w in enumerate(synth_windows):
        X_list.append(w)
        y_list.append(repouso_id)
        sources_list.append(f"synthetic_resting/{i}")

        w_mir = mirror_landmarks_x(w)
        X_list.append(w_mir)
        y_list.append(repouso_id)
        sources_list.append(f"synthetic_resting/{i}#mirror")
        extracted_counts["repouso"] += 2

    # Consolidação do Dataset
    X = np.stack(X_list, axis=0).astype(np.float32)
    y = np.array(y_list, dtype=np.int64)
    sources = np.array(sources_list, dtype=object)

    print("\n" + "=" * 70)
    print(" RESUMO FINAL DO DATASET EQUILIBRADO (4 PASTAS OFICIAIS):")
    print("=" * 70)
    for cname, cid in CLASS_MAP.items():
        cnt = np.sum(y == cid)
        pct = (cnt / len(y)) * 100
        print(f"  Classe {cid} ({cname.upper():8s}): {cnt:5d} janelas ({pct:5.1f}%)")
    print(f"  TOTAL DE AMOSTRAS: {len(y)} janelas de 60 frames")

    np.savez_compressed(OUT_NPZ, X=X, y=y, sources=sources)
    print(f"\n[SUCESSO] Dataset exportado com sucesso em: {OUT_NPZ} ({os.path.getsize(OUT_NPZ)/(1024*1024):.2f} MB)")

if __name__ == '__main__':
    main()
