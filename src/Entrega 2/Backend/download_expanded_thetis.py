import os
import sys
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos")
THETIS_BASE_URL = "https://raw.githubusercontent.com/THETIS-dataset/dataset/main/VIDEO_RGB"

# Plano de expansão com variações técnicas de iniciantes (p1 a p31) e avançados (p32 a p45)
EXPANSION_PLAN = {
    "forehand": [
        ("forehand_flat", "p{i}_foreflat_s1.avi", range(26, 41)),
        ("forehand_slice", "p{i}_fslice_s1.avi", range(1, 21)),
        ("forehand_volley", "p{i}_fvolley_s1.avi", range(1, 21)),
    ],
    "backhand": [
        ("backhand", "p{i}_backhand_s1.avi", range(26, 41)),
        ("backhand_slice", "p{i}_bslice_s1.avi", range(1, 21)),
        ("backhand_volley", "p{i}_bvolley_s1.avi", range(1, 21)),
    ],
    "saque": [
        ("flat_service", "p{i}_serflat_s1.avi", range(26, 41)),
        ("slice_service", "p{i}_serslice_s1.avi", range(1, 21)),
        ("smash", "p{i}_smash_s1.avi", range(1, 21)),
    ]
}

def download_file(url: str, dest_path: str, retries: int = 2) -> bool:
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 50000:
        return True

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=12) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            return True
        except Exception:
            if attempt == retries:
                return False
            time.sleep(0.3)
    return False

def main():
    print("=" * 70)
    print(" EXPANDINDO REPERTÓRIO THETIS COM NÍVEIS TÉCNICOS E VARIAÇÕES")
    print(" (Amadores, Slices, Voleios, Smashes e diferentes ritmos de golpe)")
    print("=" * 70)

    total_downloaded = 0
    total_skipped = 0
    total_failed = 0

    for class_name, variations in EXPANSION_PLAN.items():
        dest_dir = os.path.join(RAW_DIR, class_name)
        os.makedirs(dest_dir, exist_ok=True)
        print(f"\n-> Processando variações para classe: {class_name.upper()}")

        for cat_url, fname_pattern, id_range in variations:
            cat_count = 0
            for i in id_range:
                fname = fname_pattern.format(i=i)
                dest_path = os.path.join(dest_dir, f"thetis_{cat_url}_{fname}")
                url = f"{THETIS_BASE_URL}/{cat_url}/{fname}"

                if os.path.exists(dest_path) and os.path.getsize(dest_path) > 50000:
                    total_skipped += 1
                    continue

                ok = download_file(url, dest_path)
                if ok:
                    total_downloaded += 1
                    cat_count += 1
                else:
                    total_failed += 1

            print(f"   [{cat_url}] Baixados {cat_count} novos vídeos.")

    print(f"\n[THETIS EXPANSION CONCLUÍDO] Baixados: {total_downloaded} | Já existentes: {total_skipped} | Falhas: {total_failed}")

if __name__ == '__main__':
    main()
