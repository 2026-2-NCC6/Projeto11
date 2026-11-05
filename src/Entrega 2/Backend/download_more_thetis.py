import os
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos")
THETIS_BASE_URL = "https://raw.githubusercontent.com/THETIS-dataset/dataset/main/VIDEO_RGB"

ADDITIONAL_PLAN = {
    "forehand": [
        ("forehand_flat", "p{i}_foreflat_s1.avi", range(16, 26)),
        ("forehand_openstands", "p{i}_foreopen_s1.avi", range(16, 26))
    ],
    "backhand": [
        ("backhand", "p{i}_backhand_s1.avi", range(16, 26)),
        ("backhand2hands", "p{i}_backhand2h_s1.avi", range(16, 26))
    ],
    "saque": [
        ("flat_service", "p{i}_serflat_s1.avi", range(16, 26)),
        ("kick_service", "p{i}_serkick_s1.avi", range(16, 26))
    ]
}

def download_file(url: str, dest_path: str, retries: int = 3) -> bool:
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
                print(f"      [FALHA] {url}: {e}")
                return False
            time.sleep(0.5)
    return False

def main():
    print("=" * 65)
    print(" BAIXANDO VÍDEOS ADICIONAIS DO DATASET THETIS (p16 a p25)")
    print("=" * 65)
    
    total_downloaded = 0
    total_skipped = 0
    
    for class_name, variations in ADDITIONAL_PLAN.items():
        dest_dir = os.path.join(RAW_DIR, class_name)
        os.makedirs(dest_dir, exist_ok=True)
        print(f"\n-> Categoria: {class_name.upper()}")
        
        for category_url_name, filename_pattern, id_range in variations:
            for i in id_range:
                fname = filename_pattern.format(i=i)
                dest_path = os.path.join(dest_dir, f"thetis_{fname}")
                url = f"{THETIS_BASE_URL}/{category_url_name}/{fname}"
                
                if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
                    total_skipped += 1
                    continue
                
                print(f"   Baixando: thetis_{fname}...", end="", flush=True)
                ok = download_file(url, dest_path)
                if ok:
                    total_downloaded += 1
                    print(" OK")
                else:
                    print(" ERRO")
    
    print(f"\n[CONCLUÍDO] Baixados: {total_downloaded} | Já existentes: {total_skipped}")

if __name__ == '__main__':
    main()
