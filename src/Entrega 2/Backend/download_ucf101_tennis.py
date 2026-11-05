import os
import sys
import time
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos", "ucf101_tennis")
os.makedirs(DEST_DIR, exist_ok=True)

HF_TREE_URL = "https://huggingface.co/api/datasets/sumith2425/UCF101/tree/main/train/TennisSwing"
HF_RAW_BASE = "https://huggingface.co/datasets/sumith2425/UCF101/resolve/main/train/TennisSwing"

def main():
    print("=" * 70)
    print(" BAIXANDO SEGUNDO DATASET: UCF-101 TENNIS SWING (HUGGING FACE)")
    print(" (Vídeos 'in-the-wild' do YouTube com jogadores amadores em quadras reais)")
    print("=" * 70)

    try:
        req = urllib.request.Request(HF_TREE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            files_data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"[ERRO] Falha ao consultar lista de arquivos no HuggingFace: {e}")
        return

    video_files = [f["path"].split("/")[-1] for f in files_data if f["path"].endswith(".avi")]
    print(f"Total de vídeos de TennisSwing disponíveis no UCF-101: {len(video_files)}")

    # Selecionar uma amostra representativa de diferentes grupos de jogadores (até 50 vídeos)
    selected = video_files[:50]
    downloaded = 0
    skipped = 0

    for fname in selected:
        dest_path = os.path.join(DEST_DIR, fname)
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 50000:
            skipped += 1
            continue

        url = f"{HF_RAW_BASE}/{fname}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r, open(dest_path, "wb") as out_f:
                out_f.write(r.read())
            downloaded += 1
            print(f"   [UCF101 OK] {fname} ({os.path.getsize(dest_path) // 1024} KB)")
        except Exception as e:
            print(f"   [FALHA] {fname}: {e}")

    print(f"\n[UCF-101 DOWNLOAD CONCLUÍDO] Baixados: {downloaded} | Já existentes: {skipped} | Total na pasta: {len(os.listdir(DEST_DIR))}")

if __name__ == "__main__":
    main()
