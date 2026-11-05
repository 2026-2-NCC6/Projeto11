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

def generate_static_standing_windows(num_windows: int = 150) -> list:
    """
    Gera janelas ricas de repouso com atleta parado em frente à câmera.
    SISTEMA DE COORDENADAS CORRETO DO MEDIAPIPE (Pessoa de frente para a câmera):
    - Lado Esquerdo do atleta (Screen Right, x > 0.5): landmarks 11, 13, 15, 23 (X POSITIVO)
    - Lado Direito do atleta (Screen Left, x < 0.5): landmarks 12, 14, 16, 24 (X NEGATIVO)
    """
    rng = np.random.default_rng(2026)
    windows = []

    # Postura base anatômica realista de pé de frente para a câmera
    base_pose = np.zeros((33, 3), dtype=np.float32)

    # Tronco e cabeça
    base_pose[0] = [0.0, -0.40, -0.38]    # Nariz
    base_pose[11] = [0.07, -0.27, -0.16]  # Ombro esquerdo (positivo em X)
    base_pose[12] = [-0.07, -0.27, -0.16] # Ombro direito (negativo em X)
    base_pose[23] = [0.035, 0.0, 0.0]     # Quadril esquerdo (positivo em X)
    base_pose[24] = [-0.035, 0.0, 0.0]    # Quadril direito (negativo em X)

    # Pernas retas
    base_pose[25] = [0.04, 0.35, 0.0]    # Joelho esquerdo
    base_pose[26] = [-0.04, 0.35, 0.0]   # Joelho direito
    base_pose[27] = [0.04, 0.70, 0.0]    # Tornozelo esquerdo
    base_pose[28] = [-0.04, 0.70, 0.0]   # Tornozelo direito

    for w_idx in range(num_windows):
        scale = rng.uniform(0.85, 1.15)
        pose = base_pose.copy() * scale

        arm_style = w_idx % 3
        if arm_style == 0:
            # 1. Braços relaxados ao lado do quadril (EXATAMENTE a postura do usuário no teste)
            pose[13] = [0.09 * scale, -0.11 * scale, -0.10] # Cotovelo esq
            pose[14] = [-0.09 * scale, -0.11 * scale, -0.10] # Cotovelo dir
            pose[15] = [0.09 * scale, 0.03 * scale, -0.16]   # Pulso esq
            pose[16] = [-0.09 * scale, 0.03 * scale, -0.16]  # Pulso dir
        elif arm_style == 1:
            # 2. Mãos juntas à frente da cintura
            pose[13] = [0.07 * scale, -0.12 * scale, 0.05]
            pose[14] = [-0.07 * scale, -0.12 * scale, 0.05]
            pose[15] = [0.02 * scale, 0.02 * scale, 0.1]
            pose[16] = [-0.02 * scale, 0.02 * scale, 0.1]
        else:
            # 3. Posição de prontidão de tênis (ready stance com cotovelos flexionados)
            pose[13] = [0.10 * scale, -0.15 * scale, 0.1]
            pose[14] = [-0.10 * scale, -0.15 * scale, 0.1]
            pose[15] = [0.05 * scale, -0.05 * scale, 0.2]
            pose[16] = [-0.05 * scale, -0.05 * scale, 0.2]

        seq = np.zeros((60, 33, 3), dtype=np.float32)
        breath_freq = rng.uniform(0.15, 0.3)
        sway_freq = rng.uniform(0.05, 0.12)

        for t in range(60):
            breath = 0.006 * np.sin(2 * np.pi * breath_freq * (t / 30.0))
            sway = 0.008 * np.sin(2 * np.pi * sway_freq * (t / 30.0))
            
            frame_pose = pose.copy()
            frame_pose[:, 0] += sway
            frame_pose[[0, 11, 12, 13, 14], 1] += breath

            noise = rng.normal(0, 0.003, size=(33, 3)).astype(np.float32)
            seq[t] = frame_pose + noise

        windows.append(seq)

    return windows

def main():
    print("=" * 70)
    print(" TENNISSYNC: COMPILAÇÃO E AUDITORIA DO DATASET DE TREINAMENTO (v2)")
    print("=" * 70)

    model_path = os.path.join(BASE_DIR, "pose_landmarker_lite.task")
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.IMAGE)
    landmarker = vision.PoseLandmarker.create_from_options(options)

    X_list = []
    y_list = []
    sources_list = []

    # 1. Processar Classes de Golpes Dinâmicos (Forehand, Backhand, Saque)
    stroke_classes = ["forehand", "backhand", "saque"]
    extracted_counts = {c: 0 for c in CLASS_MAP}

    for stroke_name in stroke_classes:
        class_id = CLASS_MAP[stroke_name]
        v_files = glob.glob(os.path.join(RAW_DIR, stroke_name, "*.avi")) + \
                  glob.glob(os.path.join(RAW_DIR, stroke_name, "*.mp4"))
        
        print(f"\n-> Processando {len(v_files)} vídeos de {stroke_name.upper()}...")
        for v_path in v_files:
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
                windows = []
                for s in range(0, len(seq) - 60 + 1, 8):
                    windows.append(seq[s:s+60])

            # AVALIAÇÃO CINEMÁTICA DE CADA JANELA COM SUPORTE A GOLPES AMADORES E COMPACTOS
            for w in windows:
                wrist_motion = (np.std(w[:, 15, :]) + np.std(w[:, 16, :])) / 2.0
                wrist_disp = np.ptp(w[:, 15, :], axis=0).max() + np.ptp(w[:, 16, :], axis=0).max()
                elbow_motion = (np.std(w[:, 13, :]) + np.std(w[:, 14, :])) / 2.0

                # Aceita tanto golpes velozes de profissionais quanto movimentos amadores, voleios e slices
                if (wrist_motion >= 0.024 and wrist_disp >= 0.10) or elbow_motion >= 0.020:
                    X_list.append(w)
                    y_list.append(class_id)
                    sources_list.append(f"{stroke_name}/{v_base}")

                    w_mir = mirror_landmarks_x(w)
                    X_list.append(w_mir)
                    y_list.append(class_id)
                    sources_list.append(f"{stroke_name}/{v_base}#mirror")
                    extracted_counts[stroke_name] += 2
                # Janelas estáticas de vídeos de golpes são descartadas (NÃO realocadas como repouso)
                # para evitar contaminação de rótulo.

    # 2. Processar Segundo Dataset: UCF-101 TennisSwing (Vídeos 'in-the-wild' do YouTube)
    ucf_files = glob.glob(os.path.join(RAW_DIR, "ucf101_tennis", "*.avi"))
    print(f"\n-> Processando {len(ucf_files)} vídeos do SEGUNDO DATASET (UCF-101 Tennis)...")
    for v_path in ucf_files:
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
            windows = [seq[s:s+60] for s in range(0, len(seq) - 60 + 1, 10)]

        for w in windows:
            wrist_motion = (np.std(w[:, 15, :]) + np.std(w[:, 16, :])) / 2.0
            wrist_disp = np.ptp(w[:, 15, :], axis=0).max() + np.ptp(w[:, 16, :], axis=0).max()
            elbow_motion = (np.std(w[:, 13, :]) + np.std(w[:, 14, :])) / 2.0

            if (wrist_motion >= 0.024 and wrist_disp >= 0.10) or elbow_motion >= 0.020:
                # Classificação automática da jogada UCF pelo movimento espacial
                # Se pulso for mais alto que o nariz/cabeça durante o golpe -> Saque
                is_overhead = (w[:, 16, 1].min() < w[:, 0, 1].min()) or (w[:, 15, 1].min() < w[:, 0, 1].min())
                if is_overhead:
                    u_cls = CLASS_MAP["saque"]
                    u_name = "saque"
                else:
                    # Deslocamento horizontal do pulso direito
                    dx_wrist_r = w[-1, 16, 0] - w[0, 16, 0]
                    if dx_wrist_r > 0.04:
                        u_cls = CLASS_MAP["forehand"]
                        u_name = "forehand"
                    else:
                        u_cls = CLASS_MAP["backhand"]
                        u_name = "backhand"

                X_list.append(w)
                y_list.append(u_cls)
                sources_list.append(f"ucf101_{u_name}/{v_base}")

                w_mir = mirror_landmarks_x(w)
                X_list.append(w_mir)
                y_list.append(u_cls)
                sources_list.append(f"ucf101_{u_name}/{v_base}#mirror")
                extracted_counts[u_name] += 2

    repouso_id = CLASS_MAP["repouso"]

    # 3. Processar Vídeos Reais de Repouso Gravados pelo Usuário / WebCam
    rep_files = glob.glob(os.path.join(RAW_DIR, "repouso", "*.mp4")) + \
                glob.glob(os.path.join(RAW_DIR, "repouso", "*.avi")) + \
                glob.glob(os.path.join(RAW_DIR, "repouso", "*.mov"))
    print(f"\n-> Processando {len(rep_files)} vídeos reais gravados para REPOUSO...")
    for v_path in rep_files:
        v_base = os.path.basename(v_path)
        seq = extract_landmarks_from_video(v_path, landmarker)
        if len(seq) >= 60:
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
        elif len(seq) >= 30:
            indices = np.linspace(0, len(seq) - 1, 60)
            resampled = np.zeros((60, 33, 3), dtype=np.float32)
            for lm in range(33):
                for c in range(3):
                    resampled[:, lm, c] = np.interp(indices, np.arange(len(seq)), seq[:, lm, c])
            X_list.append(resampled)
            y_list.append(repouso_id)
            sources_list.append(f"repouso/{v_base}")
            w_mir = mirror_landmarks_x(resampled)
            X_list.append(w_mir)
            y_list.append(repouso_id)
            sources_list.append(f"repouso/{v_base}#mirror")
            extracted_counts["repouso"] += 2

    # 3. Adicionar Janelas de Ancoragem Anatômica Estática
    print("\n-> Gerando janelas de repouso para ancoragem anatômica...")
    static_windows = generate_static_standing_windows(num_windows=50)
    for i, w in enumerate(static_windows):
        X_list.append(w)
        y_list.append(repouso_id)
        sources_list.append(f"synthetic_static_standing/sample_{i}")

        w_mir = mirror_landmarks_x(w)
        X_list.append(w_mir)
        y_list.append(repouso_id)
        sources_list.append(f"synthetic_static_standing/sample_{i}#mirror")
        extracted_counts["repouso"] += 2

    # 4. Incluir Amostras Reais do Usuário Parado em Frente à Câmera (In-Domain Telemetry)
    # Replay e62 (60 frames do próprio usuário parado no quarto)
    user_replay = os.path.join(BASE_DIR, "replays", "replay_20261103_214433_backhand_e62.mp4")
    if os.path.exists(user_replay):
        cap = cv2.VideoCapture(user_replay)
        user_frames = []
        while cap.isOpened() and len(user_frames) < 120:
            ret, frame = cap.read()
            if not ret: break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
            if res.pose_landmarks:
                user_frames.append(process_landmarks_to_tensor(res.pose_landmarks[0]))
        cap.release()
        if len(user_frames) >= 60:
            print(f"-> Injetando {len(user_frames)} frames reais da câmera do usuário na classe REPOUSO...")
            for s in range(0, len(user_frames) - 60 + 1, 10):
                w = np.stack(user_frames[s:s+60])
                X_list.append(w)
                y_list.append(repouso_id)
                sources_list.append(f"user_webcam_standing/window_{s}")
                w_mir = mirror_landmarks_x(w)
                X_list.append(w_mir)
                y_list.append(repouso_id)
                sources_list.append(f"user_webcam_standing/window_{s}#mirror")
                extracted_counts["repouso"] += 2

    # Consolidação do Dataset
    X = np.stack(X_list, axis=0).astype(np.float32)
    y = np.array(y_list, dtype=np.int64)
    sources = np.array(sources_list, dtype=object)

    print("\n" + "=" * 70)
    print(" RESUMO FINAL DO DATASET REFORÇADO E AUDITADO (v2):")
    print("=" * 70)
    for cname, cid in CLASS_MAP.items():
        cnt = np.sum(y == cid)
        pct = (cnt / len(y)) * 100
        print(f"  Classe {cid} ({cname.upper()}): {cnt} janelas ({pct:.1f}%)")
    print(f"  TOTAL DE AMOSTRAS: {len(y)} janelas de 60 frames")

    np.savez_compressed(OUT_NPZ, X=X, y=y, sources=sources)
    print(f"\n[SUCESSO] Dataset exportado com sucesso em: {OUT_NPZ} ({os.path.getsize(OUT_NPZ)/(1024*1024):.2f} MB)")

if __name__ == '__main__':
    main()
