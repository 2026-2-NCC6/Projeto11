import os
import sys
import time
import urllib.request
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos")

THETIS_BASE_URL = "https://raw.githubusercontent.com/THETIS-dataset/dataset/main/VIDEO_RGB"

# Mapeamento de categorias do THETIS para as classes do TenniSync
# Selecionamos atletas p1 a p15 em duas variações de cada golpe para máxima diversidade biomecânica
DATASET_PLAN = {
    "forehand": [
        ("forehand_flat", "p{i}_foreflat_s1.avi", range(1, 16)),
        ("forehand_openstands", "p{i}_foreopen_s1.avi", range(1, 16))
    ],
    "backhand": [
        ("backhand", "p{i}_backhand_s1.avi", range(1, 16)),
        ("backhand2hands", "p{i}_backhand2h_s1.avi", range(1, 16))
    ],
    "saque": [
        ("flat_service", "p{i}_serflat_s1.avi", range(1, 16)),
        ("kick_service", "p{i}_serkick_s1.avi", range(1, 16))
    ]
}

def download_file(url: str, dest_path: str, retries: int = 3) -> bool:
    """Baixa um arquivo de forma resiliente com tentativas."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        return True

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=15) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            return True
        except Exception as e:
            if attempt == retries:
                print(f"      [FALHA] Não foi possível baixar {url}: {e}")
                return False
            time.sleep(1.0)
    return False

def extract_idle_clips_from_existing_videos(dest_repouso_dir: str, num_clips: int = 30):
    """
    Extrai clipes limpos de 2.5s (75 frames) de repouso / caminhada / espera
    a partir dos intervalos ociosos dos vídeos longos existentes em raw_videos.
    """
    print("\n-> Gerando clipes reais para a classe 'REPOUSO' a partir dos vídeos de quadra...")
    os.makedirs(dest_repouso_dir, exist_ok=True)
    
    # Fontes ricas em momentos ociosos de quadra (caminhando, esperando bola)
    source_candidates = [
        os.path.join(RAW_DIR, "forehand", "WhatsApp Video 2026-10-19 at 21.14.54.mp4"),
        os.path.join(RAW_DIR, "forehand", "WhatsApp Video 2026-10-19 at 21.18.08.mp4"),
        os.path.join(RAW_DIR, "saque", "InShot_20261019_200844592.mp4"),
        os.path.join(RAW_DIR, "saque", "InShot_20261019_201145006.mp4"),
        os.path.join(RAW_DIR, "backhand", "InShot_20261019_193124430.mp4"),
        os.path.join(RAW_DIR, "backhand", "InShot_20261019_193342849.mp4"),
    ]
    
    existing_sources = [s for s in source_candidates if os.path.exists(s)]
    if not existing_sources:
        print("   [AVISO] Nenhum vídeo longo encontrado para extração de repouso.")
        return

    clip_count = 0
    clip_duration_sec = 2.5
    
    for vidx, vpath in enumerate(existing_sources):
        if clip_count >= num_clips:
            break
            
        cap = cv2.VideoCapture(vpath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        frames_per_clip = int(fps * clip_duration_sec)
        
        # Pega amostras espaçadas (onde o jogador está aguardando ou recuperando posição)
        step_frames = int(fps * 6.0) # a cada 6 segundos
        
        for start_f in range(int(fps * 2), total_frames - frames_per_clip, step_frames):
            if clip_count >= num_clips:
                break
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
            frames = []
            for _ in range(frames_per_clip):
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                
            if len(frames) == frames_per_clip:
                clip_count += 1
                out_name = f"repouso_quadra_c{clip_count:02d}.mp4"
                out_path = os.path.join(dest_repouso_dir, out_name)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out_writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))
                for f in frames:
                    out_writer.write(f)
                out_writer.release()
                print(f"   [OK] Extraído clipe de repouso: {out_name} ({len(frames)} frames)", flush=True)

        cap.release()

    print(f"   Total de clipes de repouso gerados: {clip_count}")

def main():
    print("=" * 68)
    print(" TENNISSYNC - DOWNLOAD E COMPILAÇÃO DO DATASET DE VÍDEOS THETIS")
    print("=" * 68)
    print("Fonte: THETIS (Three-dimensional Tennis Shots Dataset)")
    print("Atletas: 15 sujeitos por golpe (homens, mulheres, destros, canhotos)")
    print("Modalidade: Câmera fixa corpo inteiro (640x480 RGB nativo)")
    print("=" * 68)

    total_downloaded = 0

    for class_name, categories in DATASET_PLAN.items():
        class_dir = os.path.join(RAW_DIR, class_name)
        os.makedirs(class_dir, exist_ok=True)
        print(f"\n-> Baixando vídeos para classe '{class_name.upper()}'...")

        class_success = 0
        for subfolder, filename_template, subject_range in categories:
            for i in subject_range:
                fname = filename_template.format(i=i)
                remote_url = f"{THETIS_BASE_URL}/{subfolder}/{fname}"
                dest_file = os.path.join(class_dir, f"thetis_{fname}")

                print(f"   [{class_name}] Baixando {fname}...", end="", flush=True)
                ok = download_file(remote_url, dest_file)
                if ok:
                    class_success += 1
                    total_downloaded += 1
                    print(" [CONCLUÍDO]", flush=True)
                else:
                    print(" [FALHOU]", flush=True)

        print(f"   Total baixado para '{class_name}': {class_success} vídeos.")

    # Gera a classe repouso
    repouso_dir = os.path.join(RAW_DIR, "repouso")
    extract_idle_clips_from_existing_videos(repouso_dir, num_clips=30)

    print("\n" + "=" * 68)
    print(" COMPILAÇÃO DO DATASET CONCLUÍDA COM SUCESSO!")
    print("=" * 68)
    print("Resumo final dos arquivos na pasta raw_videos:")
    for c in ["forehand", "backhand", "saque", "repouso"]:
        p = os.path.join(RAW_DIR, c)
        files = [f for f in os.listdir(p) if not f.startswith('.')]
        print(f"   - {c.upper():10s}: {len(files)} vídeos disponíveis")
    print("=" * 68)

if __name__ == "__main__":
    main()
