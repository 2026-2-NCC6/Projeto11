from camera_utils import get_usb_camera_source, is_camera_blacklisted
import os
import sys
import time
import argparse
import threading
import cv2
import numpy as np

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos")
DIR_FOREHAND = os.path.join(RAW_DIR, "forehand_user")
DIR_BACKHAND = os.path.join(RAW_DIR, "backhand_user")
DIR_SAQUE = os.path.join(RAW_DIR, "saque_user")

for d in [DIR_FOREHAND, DIR_BACKHAND, DIR_SAQUE]:
    os.makedirs(d, exist_ok=True)

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 12), (11, 23), (12, 24), (23, 24),
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
    (23, 25), (25, 27), (27, 29), (29, 31),
    (24, 26), (26, 28), (28, 30), (30, 32)
]

CATALOG_GOLPES = [
    # LOTE 1: BATIDAS DE DIREITA (FOREHAND)
    {
        "idx": 1,
        "class": "forehand",
        "dir": DIR_FOREHAND,
        "fname": "user_fh_01_frente_3.5m",
        "lote": "LOTE 1: BATIDAS DE DIREITA (FOREHAND)",
        "title": "BATIDA DE DIREITA DE FRENTE",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Pernas um pouco afastadas, corpo de frente para a camera",
        "acao": "Ao parar o apito: balance o braco direito para frente batendo na bola"
    },
    {
        "idx": 2,
        "class": "forehand",
        "dir": DIR_FOREHAND,
        "fname": "user_fh_02_passo_frente_3.5m",
        "lote": "LOTE 1: BATIDAS DE DIREITA (FOREHAND)",
        "title": "BATIDA DE DIREITA DANDO UM PASSO",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Corpo de lado, de um passo a frente com o pe esquerdo",
        "acao": "Gire o corpo e balance o braco com forca para frente terminando no alto"
    },
    {
        "idx": 3,
        "class": "forehand",
        "dir": DIR_FOREHAND,
        "fname": "user_fh_03_baixo_para_cima_3.5m",
        "lote": "LOTE 1: BATIDAS DE DIREITA (FOREHAND)",
        "title": "BATIDA DE DIREITA DE BAIXO PARA CIMA",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Pernas firmes no chao, joelhos levemente dobrados",
        "acao": "Comece com a mao perto da cintura e suba o braco em arco ate a cabeca"
    },
    {
        "idx": 4,
        "class": "forehand",
        "dir": DIR_FOREHAND,
        "fname": "user_fh_04_reta_e_forte_3.5m",
        "lote": "LOTE 1: BATIDAS DE DIREITA (FOREHAND)",
        "title": "BATIDA DE DIREITA RETA E FORTE",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Pernas firmes e corpo estavel",
        "acao": "Faca uma batida reta e firme para a frente na altura do umbigo"
    },
    {
        "idx": 5,
        "class": "forehand",
        "dir": DIR_FOREHAND,
        "fname": "user_fh_05_media_distancia_2.5m",
        "lote": "LOTE 1: BATIDAS DE DIREITA (FOREHAND)",
        "title": "BATIDA DE DIREITA MAIS DE PERTO",
        "dist": "Media distancia (de 1 passo a frente, ~2.5 metros)",
        "postura": "Fique um pouco mais perto da camera",
        "acao": "Faca a sua batida de direita normal, do jeito que achar mais facil"
    },

    # LOTE 2: BATIDAS DE ESQUERDA (BACKHAND)
    {
        "idx": 6,
        "class": "backhand",
        "dir": DIR_BACKHAND,
        "fname": "user_bh_06_duas_maos_3.5m",
        "lote": "LOTE 2: BATIDAS DE ESQUERDA (BACKHAND)",
        "title": "BATIDA DE ESQUERDA COM AS DUAS MAOS",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Fique de lado para a camera segurando com as duas maos juntas",
        "acao": "Puxe os bracos do lado esquerdo e jogue para frente e para cima"
    },
    {
        "idx": 7,
        "class": "backhand",
        "dir": DIR_BACKHAND,
        "fname": "user_bh_07_uma_mao_3.5m",
        "lote": "LOTE 2: BATIDAS DE ESQUERDA (BACKHAND)",
        "title": "BATIDA DE ESQUERDA COM UMA MAO SO",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Fique de lado usando apenas a sua mao direita",
        "acao": "Braco comeca recolhido e estica reto para frente abrindo o peito"
    },
    {
        "idx": 8,
        "class": "backhand",
        "dir": DIR_BACKHAND,
        "fname": "user_bh_08_cruzando_corpo_3.5m",
        "lote": "LOTE 2: BATIDAS DE ESQUERDA (BACKHAND)",
        "title": "BATIDA DE ESQUERDA CRUZANDO O CORPO",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Pernas firmes no chao, corpo virado de lado",
        "acao": "Gire o tronco e jogue o braco da esquerda para a direita na diagonal"
    },
    {
        "idx": 9,
        "class": "backhand",
        "dir": DIR_BACKHAND,
        "fname": "user_bh_09_linha_reta_3.5m",
        "lote": "LOTE 2: BATIDAS DE ESQUERDA (BACKHAND)",
        "title": "BATIDA DE ESQUERDA EM LINHA RETA",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Jogue o peso do corpo para o pe da frente",
        "acao": "Faca uma batida longa e reta para frente esticando bem os bracos"
    },
    {
        "idx": 10,
        "class": "backhand",
        "dir": DIR_BACKHAND,
        "fname": "user_bh_10_media_distancia_2.5m",
        "lote": "LOTE 2: BATIDAS DE ESQUERDA (BACKHAND)",
        "title": "BATIDA DE ESQUERDA MAIS DE PERTO",
        "dist": "Media distancia (de 1 passo a frente, ~2.5 metros)",
        "postura": "Fique um pouco mais perto da camera",
        "acao": "Faca a sua batida de esquerda natural, do jeito mais confortavel"
    },

    # LOTE 3: SAQUES (BATIDAS POR CIMA DA CABECA)
    {
        "idx": 11,
        "class": "saque",
        "dir": DIR_SAQUE,
        "fname": "user_sq_11_comum_alto_3.5m",
        "lote": "LOTE 3: SAQUES (POR CIMA DA CABECA)",
        "title": "SAQUE COMUM (JOGAR PARA O ALTO E BATER)",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Fique de lado para a camera",
        "acao": "Finja jogar a bola no alto com a mao esquerda e bata no alto com a direita"
    },
    {
        "idx": 12,
        "class": "saque",
        "dir": DIR_SAQUE,
        "fname": "user_sq_12_efeito_lado_3.5m",
        "lote": "LOTE 3: SAQUES (POR CIMA DA CABECA)",
        "title": "SAQUE CORTANDO A BOLA DE LADO",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "De lado para a camera com o braco erguido",
        "acao": "Bata no alto virando a mao de lado como se estivesse fatiando a bola"
    },
    {
        "idx": 13,
        "class": "saque",
        "dir": DIR_SAQUE,
        "fname": "user_sq_13_costas_tras_3.5m",
        "lote": "LOTE 3: SAQUES (POR CIMA DA CABECA)",
        "title": "SAQUE INCLINANDO AS COSTAS PARA TRAS",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "Incline o corpo um pouco para tras antes de bater",
        "acao": "Suba o braco por cima da cabeca e estique o corpo batendo para frente"
    },
    {
        "idx": 14,
        "class": "saque",
        "dir": DIR_SAQUE,
        "fname": "user_sq_14_dobrando_joelhos_3.5m",
        "lote": "LOTE 3: SAQUES (POR CIMA DA CABECA)",
        "title": "SAQUE DOBRANDO OS JOELHOS",
        "dist": "Fundo da sala (3.5m - corpo inteiro)",
        "postura": "De lado, junte os pes e dobre um pouco os joelhos",
        "acao": "Estique as pernas para cima e bata no ponto mais alto com a mao direita"
    },
    {
        "idx": 15,
        "class": "saque",
        "dir": DIR_SAQUE,
        "fname": "user_sq_15_media_distancia_2.5m",
        "lote": "LOTE 3: SAQUES (POR CIMA DA CABECA)",
        "title": "SAQUE MAIS DE PERTO",
        "dist": "Media distancia (de 1 passo a frente, ~2.5 metros)",
        "postura": "Fique um pouco mais perto da camera",
        "acao": "Faca o movimento de saque natural esticando o braco no alto"
    }
]
def play_beep_async(freq, duration_ms):
    if HAS_SOUND:
        try:
            t = threading.Thread(target=lambda: winsound.Beep(freq, duration_ms), daemon=True)
            t.start()
            return t
        except Exception:
            pass
    return None

def draw_mediapipe_skeleton(display, landmarks, width, height):
    if not landmarks or len(landmarks) < 25:
        return

    for i, j in POSE_CONNECTIONS:
        if i < len(landmarks) and j < len(landmarks):
            lm_i = landmarks[i]
            lm_j = landmarks[j]
            vis_i = getattr(lm_i, 'visibility', 1.0)
            vis_j = getattr(lm_j, 'visibility', 1.0)
            if vis_i > 0.35 and vis_j > 0.35:
                x1, y1 = int(lm_i.x * width), int(lm_i.y * height)
                x2, y2 = int(lm_j.x * width), int(lm_j.y * height)
                cv2.line(display, (x1, y1), (x2, y2), (0, 230, 140), 2, cv2.LINE_AA)

    for idx, lm in enumerate(landmarks):
        vis = getattr(lm, 'visibility', 1.0)
        if vis > 0.35:
            cx, cy = int(lm.x * width), int(lm.y * height)
            if idx in [15, 16, 17, 18, 19, 20, 21, 22]:
                cv2.circle(display, (cx, cy), 5, (255, 190, 0), -1, cv2.LINE_AA)
            elif idx in [11, 12, 13, 14, 23, 24, 25, 26, 27, 28]:
                cv2.circle(display, (cx, cy), 6, (0, 215, 255), -1, cv2.LINE_AA)
                cv2.circle(display, (cx, cy), 7, (255, 255, 255), 1, cv2.LINE_AA)
            elif idx in [0, 2, 5, 7, 8]:
                cv2.circle(display, (cx, cy), 4, (0, 240, 255), -1, cv2.LINE_AA)

def run_golpes_session(cap, landmarker, start_idx=1, end_idx=10, briefing_sec=14, countdown_sec=8, duration_sec=6.5):
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = 30.0

    print("=" * 75)
    print(" TENNISSYNC: GRAVADOR GUIADO DE GOLPES AO FUNDO (15 VÍDEOS)")
    print(" - 5 Forehands + 5 Backhands + 5 Saques a 3.5m e média distância")
    print(" - Rastreamento MediaPipe Pose 3D ao vivo na tela")
    print(" - Beep de 5 segundos de preparação -> Gravação de 6 segundos do golpe")
    print(" - Controles: [ESPAÇO]: Gravar Já | [P]: Pausar | [R]: Regravar | [S]: Pular | [Q]: Sair")
    print("=" * 75)

    catalog_map = {item["idx"]: item for item in CATALOG_GOLPES}

    # Detecta se há vídeos já gravados no intervalo selecionado para continuar de onde parou
    current_idx = start_idx
    for item in CATALOG_GOLPES:
        if item["idx"] < start_idx:
            continue
        if item["idx"] > end_idx:
            break
        p = os.path.join(item["dir"], f"{item['fname']}.mp4")
        if os.path.exists(p) and os.path.getsize(p) > 20000:
            current_idx = item["idx"] + 1

    if current_idx > end_idx:
        print(f"[INFO] Todos os vídeos de {start_idx} a {end_idx} já foram gravados! Reiniciando no vídeo {start_idx}...")
        current_idx = start_idx

    while current_idx <= end_idx:
        item = catalog_map.get(current_idx)
        if not item:
            break

        idx = item["idx"]
        fname = item["fname"]
        title = item["title"]
        lote_name = item["lote"]
        dist = item["dist"]
        postura = item["postura"]
        acao = item["acao"]
        dest_dir = item["dir"]
        out_path = os.path.join(dest_dir, f"{fname}.mp4")

        print(f"\n>>> [GOLPE {idx:02d}/{end_idx:02d}]: {title} ({item['class'].upper()})")
        print(f"    Enquadramento: {dist}")
        print(f"    Postura: {postura}")
        print(f"    Ação: {acao}")

        play_beep_async(600, 120)

        # ----------------------------------------------------
        # FASE 1: BRIEFING NA TELA (com auto-avanço de 8s)
        # ----------------------------------------------------
        b_start = time.time()
        is_paused = False

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            if not is_paused:
                b_elapsed = time.time() - b_start
                b_rem = max(0, briefing_sec - int(b_elapsed))
            else:
                b_rem = 0

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_img)

            display = frame.copy()
            if res.pose_landmarks:
                draw_mediapipe_skeleton(display, res.pose_landmarks[0], width, height)

            # Header
            cv2.rectangle(display, (0, 0), (width, 50), (15, 18, 24), -1)
            cv2.putText(display, f"[{idx:02d}/{end_idx:02d}] {title}", (14, 25), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 230, 140), 2)
            cv2.putText(display, f"{lote_name}  -  {dist}", (14, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 215, 255), 1)

            # Card de Instruções
            card_y = height - 150
            cv2.rectangle(display, (10, card_y), (width - 10, height - 40), (12, 14, 18), -1)
            cv2.rectangle(display, (10, card_y), (width - 10, height - 40), (0, 230, 140), 1)

            cv2.putText(display, f"INSTRUCAO DO GOLPE {idx:02d}/{end_idx:02d}:", (20, card_y + 22), cv2.FONT_HERSHEY_DUPLEX, 0.50, (0, 230, 140), 1)
            cv2.putText(display, f"ONDE FICAR: {dist}", (20, card_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 215, 255), 1)
            cv2.putText(display, f"POSTURA: {postura}", (20, card_y + 68), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1)
            cv2.putText(display, f"MOVIMENTO: {acao}", (20, card_y + 91), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 230, 200), 1)

            # Barra inferior
            cv2.rectangle(display, (10, height - 32), (width - 10, height - 10), (20, 24, 30), -1)
            if is_paused:
                cv2.putText(display, "[PAUSADO] Pressione [ESPACO] para iniciar a gravacao deste golpe", (20, height - 17), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 215, 255), 1)
            else:
                cv2.putText(display, f"INICIANDO EM: {b_rem}s  |  [ESPACO]: Gravar Agora  |  [P]: Pausar  |  [R]: Voltar  |  [Q]: Sair", 
                            (20, height - 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (170, 170, 170), 1)

            cv2.imshow("TenniSync - Gravador de Golpes com MediaPipe 3D", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n[ENCERRADO PELO USUÁRIO]")
                return
            elif key == ord('p'):
                is_paused = not is_paused
            elif key == 32 or key == 13: # Espaço ou Enter
                break
            elif key == ord('s'):
                print(f"[PULADO] Golpe {idx:02d} pulado.")
                current_idx += 1
                break
            elif key == ord('r'):
                current_idx = max(1, current_idx - 1)
                break

            if not is_paused and b_elapsed >= briefing_sec:
                break

        if key in [ord('s'), ord('r')]:
            continue

        # ----------------------------------------------------
        # FASE 2: BEEP CONTÍNUO DE 5 SEGUNDOS (PREPARAÇÃO)
        # ----------------------------------------------------
        print(f" -> Contagem de {countdown_sec}s com BEEP CONTÍNUO... Posicione-se a {dist}!")
        play_beep_async(900, int(countdown_sec * 1000))

        c_start = time.time()
        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            c_elapsed = time.time() - c_start
            c_rem = countdown_sec - int(c_elapsed)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_img)

            display = frame.copy()
            if res.pose_landmarks:
                draw_mediapipe_skeleton(display, res.pose_landmarks[0], width, height)

            cv2.rectangle(display, (0, 0), (width, 50), (15, 18, 24), -1)
            cv2.putText(display, f"[{idx:02d}/{end_idx:02d}] {title}", (14, 25), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 230, 140), 2)
            cv2.putText(display, f"PREPARE-SE PARA O GOLPE  -  {dist}", (14, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 215, 255), 1)

            cv2.rectangle(display, (width // 2 - 210, height // 2 - 45), (width // 2 + 210, height // 2 + 35), (10, 12, 16), -1)
            cv2.rectangle(display, (width // 2 - 210, height // 2 - 45), (width // 2 + 210, height // 2 + 35), (0, 215, 255), 2)
            if c_rem > 0:
                cv2.putText(display, f"POSICIONE-SE: {c_rem}s", (width // 2 - 170, height // 2), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 215, 255), 2)
                cv2.putText(display, "Ouvindo Beep continuo...", (width // 2 - 130, height // 2 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 230, 140), 1)
            else:
                cv2.putText(display, "GOLPEIE AGORA!", (width // 2 - 170, height // 2 + 5), cv2.FONT_HERSHEY_DUPLEX, 1.15, (0, 0, 255), 2)

            cv2.imshow("TenniSync - Gravador de Golpes com MediaPipe 3D", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[ENCERRADO PELO USUÁRIO]")
                return

            if c_elapsed >= countdown_sec:
                break

        # ----------------------------------------------------
        # FASE 3: GRAVAÇÃO ATIVA DO GOLPE (6 SEGUNDOS)
        # ----------------------------------------------------
        print(f" -> [BEEP PAROU: GRAVANDO GOLPE REAL {fname}.mp4 POR {duration_sec}s! GOLPEIE!]")
        recorded_frames = []
        r_start = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            r_elapsed = time.time() - r_start
            rem_rec = duration_sec - r_elapsed

            recorded_frames.append(frame.copy())

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_img)

            display = frame.copy()
            if res.pose_landmarks:
                draw_mediapipe_skeleton(display, res.pose_landmarks[0], width, height)

            # Header de Gravação Ativa (Vermelho)
            cv2.rectangle(display, (0, 0), (width, 50), (10, 10, 40), -1)
            cv2.circle(display, (26, 25), 10, (0, 0, 255), -1)
            cv2.putText(display, f"GRAVANDO: [{idx:02d}/{end_idx:02d}] {title} ({rem_rec:.1f}s)", (48, 28), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 0, 255), 2)
            cv2.putText(display, f"EXECUTE O GOLPE AGORA: {acao}", (48, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 255), 1)

            # Barra de progresso verde
            bar_w = int((r_elapsed / duration_sec) * (width - 20))
            cv2.rectangle(display, (10, height - 20), (width - 10, height - 10), (40, 40, 40), -1)
            cv2.rectangle(display, (10, height - 20), (10 + bar_w, height - 10), (0, 230, 140), -1)

            cv2.imshow("TenniSync - Gravador de Golpes com MediaPipe 3D", display)
            cv2.waitKey(1)

            if r_elapsed >= duration_sec:
                break

        # ----------------------------------------------------
        # FASE 4: SALVAMENTO E CHIME DUPLO
        # ----------------------------------------------------
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, 30.0, (width, height))
        for rf in recorded_frames:
            writer.write(rf)
        writer.release()

        sz_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f" -> OK: Salvo '{os.path.basename(out_path)}' ({sz_mb:.2f} MB, {len(recorded_frames)} frames)")

        # Chime duplo agudo confirmando sucesso
        if HAS_SOUND:
            play_beep_async(1200, 140)
            time.sleep(0.15)
            play_beep_async(1600, 220)

        current_idx += 1
        time.sleep(1.0)

    print("\n" + "=" * 75)
    print(f" SUCESSO! GRAVACAO DOS VIDEOS {start_idx:02d} A {end_idx:02d} CONCLUIDA!")
    print("=" * 75)

def main():
    parser = argparse.ArgumentParser(description="Gravador guiado de golpes reais de tênis ao fundo.")
    parser.add_argument("--camera", type=int, default=0, help="Índice da webcam (padrão: 0).")
    parser.add_argument("--start", type=int, default=1, help="Índice inicial do vídeo (padrão: 1).")
    parser.add_argument("--end", type=int, default=10, help="Índice final do vídeo (padrão: 10 para regravar Forehand e Backhand).")
    parser.add_argument("--briefing", type=int, default=14, help="Tempo para leitura das instruções na tela em segundos (padrão: 14s).")
    parser.add_argument("--countdown", type=int, default=8, help="Tempo do beep contínuo de preparação em segundos (padrão: 8s).")
    parser.add_argument("--duration", type=float, default=6.5, help="Duração da gravação do golpe em segundos (padrão: 6.5s).")
    args = parser.parse_args()

    model_path = os.path.join(BASE_DIR, "pose_landmarker_full.task")
    if not os.path.exists(model_path):
        model_path = os.path.join(BASE_DIR, "pose_landmarker_lite.task")

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    # Abre câmera (tenta DirectShow primeiro para evitar travamentos no Windows)
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera)

    if not cap.isOpened():
        print(f"[ERRO] Não foi possível abrir a câmera índice {args.camera}.")
        sys.exit(1)

    try:
        run_golpes_session(cap, landmarker, start_idx=args.start, end_idx=args.end, briefing_sec=args.briefing, countdown_sec=args.countdown, duration_sec=args.duration)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()

if __name__ == "__main__":
    main()
