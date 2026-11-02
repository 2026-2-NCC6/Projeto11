import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def main():
    print("=" * 70, flush=True)
    print("      TENNISSYNC - PIPELINE DE EXTRAÇÃO E TREINAMENTO AO VIVO", flush=True)
    print("=" * 70, flush=True)

    # 1. Extração do Dataset
    print("\n[ETAPA 1/2] Iniciando extração dos 33 Landmarks 3D via MediaPipe...", flush=True)
    extract_cmd = [
        sys.executable, "-u", os.path.join(BASE_DIR, "extract_dataset.py"),
        "--augment-mirror"
    ]
    ret_extract = subprocess.run(extract_cmd, cwd=BASE_DIR)
    if ret_extract.returncode != 0:
        print("\n[ERRO] Falha durante a extração do dataset!", flush=True)
        sys.exit(ret_extract.returncode)

    # 2. Treinamento da Rede Neural Transformer
    print("\n" + "=" * 70, flush=True)
    print("[ETAPA 2/2] Iniciando treinamento da Rede Neural TennisTransformerGPU...", flush=True)
    print("=" * 70, flush=True)
    train_cmd = [
        sys.executable, "-u", os.path.join(BASE_DIR, "train_model.py"),
        "--epochs", "45",
        "--batch-size", "16"
    ]
    ret_train = subprocess.run(train_cmd, cwd=BASE_DIR)
    if ret_train.returncode != 0:
        print("\n[ERRO] Falha durante o treinamento do modelo!", flush=True)
        sys.exit(ret_train.returncode)

    print("\n" + "=" * 70, flush=True)
    print(" [SUCESSO COMPLETO] O modelo TennisTransformer foi treinado e os pesos", flush=True)
    print(" foram salvos em: models/weights/tennis_transformer_weights.pth", flush=True)
    print(" O sistema está pronto para inferência em tempo real via pose_estimation.py!", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
