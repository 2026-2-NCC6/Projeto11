import os
import math
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

CLASS_MAP = {
    "forehand": 0,
    "backhand": 1,
    "saque": 2,
    "repouso": 3
}

ID_TO_CLASS = {v: k.capitalize() for k, v in CLASS_MAP.items()}


if HAS_TORCH:
    class PositionalEncoding(nn.Module):
        """
        Codificação posicional senoidal para preservar a ordem temporal dos 60 frames.
        """
        def __init__(self, d_model: int, max_len: int = 120, dropout: float = 0.1):
            super().__init__()
            self.dropout = nn.Dropout(p=dropout)

            position = torch.arange(max_len).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
            pe = torch.zeros(1, max_len, d_model)
            pe[0, :, 0::2] = torch.sin(position * div_term)
            pe[0, :, 1::2] = torch.cos(position * div_term)
            self.register_buffer('pe', pe)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            x: Tensor de shape (Batch, SeqLen, d_model)
            """
            x = x + self.pe[:, :x.size(1), :]
            return self.dropout(x)


    class TennisTransformerNet(nn.Module):
        """
        Rede Neural Transformer para classificação temporal de golpes de tênis.
        Entrada: (Batch, 60, 33, 3) -> 60 frames, 33 landmarks 3D (X, Y, Z centralizados no quadril)
        Saída: Logits de shape (Batch, 4) -> [Forehand, Backhand, Saque, Repouso]
        """
        def __init__(
            self,
            num_landmarks: int = 33,
            coords_per_landmark: int = 3,
            seq_len: int = 60,
            d_model: int = 128,
            nhead: int = 4,
            num_layers: int = 3,
            dim_feedforward: int = 256,
            num_classes: int = 4,
            dropout: float = 0.2
        ):
            super().__init__()
            self.input_dim = num_landmarks * coords_per_landmark  # 33 * 3 = 99
            self.seq_len = seq_len
            self.d_model = d_model

            # Projeção linear das 99 coordenadas espaciais para d_model
            self.input_projection = nn.Sequential(
                nn.Linear(self.input_dim, d_model),
                nn.LayerNorm(d_model),
                nn.ReLU(),
                nn.Dropout(dropout)
            )

            self.pos_encoder = PositionalEncoding(d_model=d_model, max_len=max(seq_len, 120), dropout=dropout)

            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=nhead,
                dim_feedforward=dim_feedforward,
                dropout=dropout,
                batch_first=True,
                activation="gelu"
            )
            self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

            # Cabeça de classificação após Global Average + Max Pooling temporal
            self.classifier = nn.Sequential(
                nn.Linear(d_model * 2, d_model),
                nn.LayerNorm(d_model),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model, num_classes)
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            Aceita tensores de shape (Batch, Frames, 33, 3) ou (Batch, Frames, 99).
            Retorna logits de shape (Batch, num_classes).
            """
            if x.dim() == 4:
                batch_size, seq_len, num_lm, coords = x.shape
                x = x.reshape(batch_size, seq_len, num_lm * coords)

            x = self.input_projection(x)
            x = self.pos_encoder(x)
            x = self.transformer_encoder(x)

            # Combina média temporal e pico temporal (importante para capturar o ápice do golpe)
            avg_pool = x.mean(dim=1)
            max_pool, _ = x.max(dim=1)
            pooled = torch.cat([avg_pool, max_pool], dim=-1)

            logits = self.classifier(pooled)
            return logits


class TennisTransformerGPU:
    """
    Wrapper de inferência compatível com o pipeline pose_estimation.py.
    Carrega automaticamente os pesos treinados em `models/weights/tennis_transformer_weights.pth`
    se existirem; caso contrário, opera em modo Mock de segurança.
    """
    def __init__(self, weights_path: str = None):
        self.device = "cpu"
        self.is_trained = False
        self.model = None

        if weights_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            weights_path = os.path.join(base_dir, "weights", "tennis_transformer_weights.pth")
        self.weights_path = weights_path

        if HAS_TORCH:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = TennisTransformerNet().to(self.device)
            self.model.eval()

            if os.path.exists(self.weights_path):
                try:
                    checkpoint = torch.load(self.weights_path, map_location=self.device, weights_only=False)
                    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                        self.model.load_state_dict(checkpoint["model_state_dict"])
                    else:
                        self.model.load_state_dict(checkpoint)
                    self.is_trained = True
                    print(f"TennisTransformerGPU: Pesos treinados carregados com sucesso de '{self.weights_path}' ({self.device}).")
                except Exception as e:
                    print(f"Aviso: Falha ao carregar pesos em '{self.weights_path}': {e}. Usando modo Mock.")
            else:
                print(
                    f"TennisTransformerGPU: Arquivo de pesos não encontrado em '{self.weights_path}'.\n"
                    " -> Operando em modo Mock até que o treinamento (train_model.py) seja executado."
                )
        else:
            print("TennisTransformerGPU: PyTorch não instalado. Operando em modo Mock.")

    def __call__(self, input_tensor):
        """
        Recebe um tensor ou array de shape (Batch, Frames, Landmarks, Coords) -> (1, 60, 33, 3)
        Retorna (class_id, confidence)
        class_id: 0 = Forehand, 1 = Backhand, 2 = Saque, 3 = Repouso
        """
        if HAS_TORCH and self.is_trained and self.model is not None:
            with torch.no_grad():
                if not isinstance(input_tensor, torch.Tensor):
                    tensor = torch.tensor(input_tensor, dtype=torch.float32, device=self.device)
                else:
                    tensor = input_tensor.to(self.device, dtype=torch.float32)

                logits = self.model(tensor)
                probs = F.softmax(logits, dim=-1)
                conf, pred = torch.max(probs, dim=-1)
                return int(pred.item()), float(conf.item())

        # Fallback Mock caso os pesos ainda não tenham sido treinados
        chance = np.random.rand()
        if chance > 0.95:
            return 2, 0.92
        elif chance > 0.90:
            return 0, 0.88
        else:
            return 3, 0.99

    def to(self, device: str):
        """Move o modelo para o dispositivo especificado (com fallback seguro para CPU se CUDA indisponível)."""
        if HAS_TORCH and self.model is not None:
            if device == "cuda" and not torch.cuda.is_available():
                print("TennisTransformerGPU: CUDA não disponível nesta máquina. Mantendo em CPU.")
                self.device = "cpu"
            else:
                self.device = device
            self.model = self.model.to(self.device)
            print(f"TennisTransformerGPU: Dispositivo configurado para '{self.device}'.")
        else:
            print(f"TennisTransformerGPU (Mock): Simulando alocação em {device}.")
        return self
