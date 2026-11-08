import os
import sys
import time
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos", "repouso_internet")
os.makedirs(DEST_DIR, exist_ok=True)

TARGET_CLASSES = [
    "Typing",           # Pessoa sentada à mesa com mãos no teclado
    "WritingOnBoard",   # Pessoa de pé fazendo gestos casuais com um braço
    "WalkingWithDog",   # Pessoa caminhando casualmente
    "Haircut",          # Pessoa sentada em repouso
    "HeadMassage",      # Pessoa sentada imóvel/relaxada
    "Billiards"         # Pessoa de pé observando / movimentos suaves
]

def main():
    print("=" * 70)
    print(" BAIXANDO DATASET DE VÍDEOS DE REPOUSO / ATIVIDADES CASUAIS DA INTERNET")
    print(" (UCF-101: Pessoas reais sentadas, em pé, digitando, caminhando e relaxadas)")
    print("=" * 70)

    total_downloaded = 0
    total_skipped = 0

    for cls in TARGET_CLASSES:
        tree_url = f"https://huggingface.co/api/datasets/sumith2425/UCF101/tree/main/train/{cls}"
        raw_base = f"https://huggingface.co/datasets/sumith2425/UCF101/resolve/main/train/{cls}"
        
        try:
            req = urllib.request.Request(tree_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                files_data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"[AVISO] Falha ao listar classe {cls}: {e}")
            continue

        video_files = [f["path"].split("/")[-1] for f in files_data if f["path"].endswith(".avi")]
        # Pega até 7 vídeos por classe
        selected = video_files[:7]
        print(f"\n-> Classe '{cls}': {len(video_files)} disponíveis, baixando {len(selected)} amostras...")

        for fname in selected:
            dest_name = f"ucf_repouso_{cls.lower()}_{fname}"
            dest_path = os.path.join(DEST_DIR, dest_name)
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 30000:
                total_skipped += 1
                continue

            url = f"{raw_base}/{fname}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as r, open(dest_path, "wb") as out_f:
                    out_f.write(r.read())
                total_downloaded += 1
                print(f"   [OK] {dest_name} ({os.path.getsize(dest_path) // 1024} KB)")
            except Exception as e:
                print(f"   [FALHA] {fname}: {e}")

    print(f"\n[DOWNLOAD REPOUSO INTERNET CONCLUÍDO] Baixados: {total_downloaded} | Existentes: {total_skipped} | Total: {len(os.listdir(DEST_DIR))}")

if __name__ == "__main__":
    main()
