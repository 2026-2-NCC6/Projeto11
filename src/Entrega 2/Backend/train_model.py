import os
import sys
import argparse
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    print("[ERRO] PyTorch não encontrado! Instale com: pip install torch")
    sys.exit(1)

from models.tennis_transformer import TennisTransformerNet, CLASS_MAP, ID_TO_CLASS


class TennisPoseDataset(Dataset):
    """
    Dataset PyTorch para janelas temporais de landmarks 3D (60, 33, 3).
    Inclui Data Augmentation leve durante o treino (ruído gaussiano e escala).
    """
    def __init__(self, X: np.ndarray, y: np.ndarray, training: bool = False):
        self.X = X.astype(np.float32)
        self.y = y.astype(np.int64)
        self.training = training

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        sample = self.X[idx].copy()
        label = self.y[idx]

        if self.training:
            # Escala espacial aleatória (+/- 8%) para simular atletas de diferentes estaturas/distâncias
            scale = np.random.uniform(0.92, 1.08)
            sample = sample * scale

            # Jitter gaussiano leve para robustez contra ruído do sensor/MediaPipe
            noise = np.random.normal(0.0, 0.008, size=sample.shape).astype(np.float32)
            sample = sample + noise

            # Jitter adversarial nas maos (falanges 17 a 22):
            hand_noise = np.random.normal(0.0, 0.05, size=(60, 6, 3)).astype(np.float32)
            sample[:, [17, 18, 19, 20, 21, 22], :] += hand_noise

            # 4. Leg Dropout / Masking (Invariância Total de Membros Inferiores):
            # Em 50% dos batches, zera pernas/quadris (landmarks 23 a 32)
            # Força o Transformer a aprender a cinemática de golpes exclusivamente pelo trem superior
            if np.random.rand() < 0.50:
                sample[:, 23:, :] = 0.0

        return torch.tensor(sample, dtype=torch.float32), torch.tensor(label, dtype=torch.long)


def split_train_val(X: np.ndarray, y: np.ndarray, val_ratio: float = 0.2, seed: int = 42):
    """
    Divide o dataset de forma estratificada por classe entre treino e validação.
    """
    rng = np.random.default_rng(seed)
    train_indices = []
    val_indices = []

    for cid in np.unique(y):
        cls_idx = np.where(y == cid)[0]
        rng.shuffle(cls_idx)
        n_val = max(1, int(len(cls_idx) * val_ratio)) if len(cls_idx) >= 4 else 0
        val_indices.extend(cls_idx[:n_val])
        train_indices.extend(cls_idx[n_val:])

    train_indices = np.array(train_indices, dtype=np.int64)
    val_indices = np.array(val_indices, dtype=np.int64)
    return (X[train_indices], y[train_indices]), (X[val_indices], y[val_indices])


def compute_confusion_matrix(preds: list, targets: list, num_classes: int = 4) -> np.ndarray:
    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for p, t in zip(preds, targets):
        if 0 <= t < num_classes and 0 <= p < num_classes:
            cm[t, p] += 1
    return cm


def main():
    parser = argparse.ArgumentParser(description="Treina o modelo TennisTransformerNet com os vídeos extraídos.")
    parser.add_argument("--data", type=str, default=os.path.join(BASE_DIR, "dataset", "processed", "tennis_dataset.npz"),
                        help="Caminho para o arquivo tennis_dataset.npz.")
    parser.add_argument("--weights-out", type=str,
                        default=os.path.join(BASE_DIR, "models", "weights", "tennis_transformer_weights.pth"),
                        help="Caminho onde os melhores pesos serão salvos.")
    parser.add_argument("--epochs", type=int, default=45, help="Número de épocas de treinamento (padrão: 45).")
    parser.add_argument("--batch-size", type=int, default=16, help="Tamanho do batch (padrão: 16).")
    parser.add_argument("--lr", type=float, default=1e-3, help="Taxa de aprendizado inicial (padrão: 1e-3).")
    parser.add_argument("--synthetic-demo", action="store_true",
                        help="Executa um treino rápido com dados sintéticos para validar todo o pipeline.")
    args = parser.parse_args()

    if args.synthetic_demo:
        print("[MODO DEMO] Gerando dados sintéticos (80 amostras, 4 classes) para validar o pipeline...")
        rng = np.random.default_rng(42)
        X = rng.normal(0, 0.25, size=(80, 60, 33, 3)).astype(np.float32)
        y = np.repeat([0, 1, 2, 3], 20).astype(np.int64)
        # Adiciona assinaturas sintéticas distintas por classe para convergir no teste
        for cid in range(4):
            X[y == cid, :, cid * 5:(cid + 1) * 5, 0] += (cid + 1) * 0.6
    else:
        if not os.path.exists(args.data):
            print(f"[ERRO] Arquivo de dataset não encontrado: {args.data}")
            print(" -> Execute primeiro: python extract_dataset.py")
            sys.exit(1)

        loaded = np.load(args.data, allow_pickle=True)
        X, y = loaded["X"], loaded["y"]

    print("=" * 65)
    print(" TENNISSYNC - TREINAMENTO DO MODELO TENNISTRANSFORMER")
    print("=" * 65)
    print(f" Total de amostras : {len(y)} | Shape: {X.shape}")

    (X_train, y_train), (X_val, y_val) = split_train_val(X, y, val_ratio=0.2)
    print(f" Amostras Treino   : {len(y_train)} | Validação: {len(y_val)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f" Dispositivo ativo : {device.upper()}")

    train_ds = TennisPoseDataset(X_train, y_train, training=True)
    val_ds = TennisPoseDataset(X_val, y_val, training=False) if len(y_val) > 0 else None

    train_loader = DataLoader(train_ds, batch_size=min(args.batch_size, len(train_ds)), shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=min(args.batch_size, len(val_ds)), shuffle=False) if val_ds else None

    # Pesos inversamente proporcionais à frequência de cada classe para evitar viés em datasets desbalanceados
    class_counts = np.array([max(1, np.sum(y_train == c)) for c in range(4)], dtype=np.float32)
    class_weights = torch.tensor(len(y_train) / (4.0 * class_counts), dtype=torch.float32, device=device)

    model = TennisTransformerNet(num_classes=4).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = -1.0
    best_preds, best_targets = [], []

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * len(batch_y)
            preds = logits.argmax(dim=-1)
            train_correct += (preds == batch_y).sum().item()
            train_total += len(batch_y)

        scheduler.step()
        train_acc = (train_correct / max(1, train_total)) * 100.0
        avg_loss = train_loss / max(1, train_total)

        if val_loader:
            model.eval()
            val_correct = 0
            val_total = 0
            epoch_preds, epoch_targets = [], []
            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                    logits = model(batch_x)
                    preds = logits.argmax(dim=-1)
                    val_correct += (preds == batch_y).sum().item()
                    val_total += len(batch_y)
                    epoch_preds.extend(preds.cpu().tolist())
                    epoch_targets.extend(batch_y.cpu().tolist())

            val_acc = (val_correct / max(1, val_total)) * 100.0
        else:
            val_acc = train_acc
            epoch_preds, epoch_targets = [], []

        # Imprime todas as épocas com flush=True imediato para feedback visual contínuo
        progress_bar = "=" * int((epoch / args.epochs) * 20) + "-" * (20 - int((epoch / args.epochs) * 20))
        print(f" Época [{epoch:02d}/{args.epochs:02d}] [{progress_bar}] | Loss: {avg_loss:.4f} | Treino Acc: {train_acc:6.2f}% | Val Acc: {val_acc:6.2f}%", flush=True)

        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            best_preds, best_targets = epoch_preds, epoch_targets
            os.makedirs(os.path.dirname(args.weights_out), exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_acc": best_val_acc,
                "class_map": CLASS_MAP
            }, args.weights_out)

    print("\n" + "=" * 65)
    print(f" TREINAMENTO CONCLUÍDO! Melhor Acurácia de Validação: {best_val_acc:.2f}%")
    print(f" Pesos salvos em: {args.weights_out}")

    if best_targets:
        cm = compute_confusion_matrix(best_preds, best_targets, num_classes=4)
        print("\n Matriz de Confusão (Linhas = Real, Colunas = Predito):")
        header = "             " + " ".join(f"{ID_TO_CLASS[i][:8]:>9s}" for i in range(4))
        print(header)
        for i in range(4):
            row_str = " ".join(f"{cm[i, j]:9d}" for j in range(4))
            print(f" {ID_TO_CLASS[i]:11s} {row_str}")
    print("=" * 65)


if __name__ == "__main__":
    main()
