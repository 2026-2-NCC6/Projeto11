# Guia de Coleta de Vídeos e Treinamento (`TennisTransformerGPU`)

Este diretório armazena os vídeos brutos e os datasets processados para treinar o modelo classificador temporal de golpes do **TennisSync**.

---

## 📂 1. Onde colocar os vídeos?

Coloque os seus arquivos de vídeo (`.mp4`, `.mov`, `.avi`, `.mkv` ou `.webm`) dentro das respectivas subpastas em `raw_videos/`:

```text
dataset/
├── raw_videos/
│   ├── forehand/    <-- Vídeos executando Forehand (Classe 0)
│   ├── backhand/    <-- Vídeos executando Backhand (Classe 1)
│   ├── saque/       <-- Vídeos executando Saque (Classe 2)
│   └── repouso/     <-- Vídeos em posição de espera / caminhando / sem golpear (Classe 3)
└── processed/
    └── tennis_dataset.npz  <-- Gerado automaticamente pelo script extract_dataset.py
```

---

## 🎥 2. Recomendações para Gravação dos Vídeos

1. **Corpo Inteiro Visível:** O atleta deve aparecer dos pés à cabeça (inclusive com a raquete erguida no saque) para que o MediaPipe extraia os 33 landmarks sem oclusão.
2. **Duração dos Clipes:**
   - **Opção A (Recomendada - Clipes por golpe):** Vídeos curtos de **2 a 3 segundos** (60 a 90 frames a 30 FPS) contendo 1 golpe completo (preparação $\rightarrow$ impacto $\rightarrow$ terminação).
   - **Opção B (Vídeo contínuo):** Um vídeo mais longo contendo vários golpes da mesma classe em sequência (desde que não haja longos períodos parado se for nas pastas de golpe).
3. **Importância da classe `repouso`:** Grave também vídeos do jogador parado em *split-step*, esperando a bola ou caminhando na quadra. Isso evita falsos positivos enquanto o atleta não está batendo na bola.
4. **Quantidade sugerida para início:**
   - Mínimo funcional para primeiros testes: **15 a 20 vídeos por classe**.
   - Recomendado para boa generalização: **40 a 60+ vídeos por classe** (você pode usar `--augment-mirror` na extração para dobrar as amostras automaticamente).

---

## 🚀 3. Passo a Passo para Treinar o Modelo

Execute os comandos abaixo a partir da pasta `src/Entrega 2/Backend`:

### Passo 3.1 (Opcional): Gravar vídeos direto pela Webcam
Se quiser gravar os vídeos já organizados nas pastas certas usando a própria câmera do computador:
```bash
python record_training_videos.py --camera 0
```
*(Na tela que abrir, pressione `1` para Forehand, `2` para Backhand, `3` para Saque e `4` para Repouso).*

### Passo 3.2: Extrair os Landmarks 3D dos vídeos
Processa todos os vídeos de `dataset/raw_videos/`, centraliza as coordenadas pelo quadril, aplica suavização temporal e gera o arquivo `dataset/processed/tennis_dataset.npz`:
```bash
python extract_dataset.py --augment-mirror
```

### Passo 3.3: Treinar a Rede Neural (`TennisTransformerNet`)
Treina o modelo Transformer e salva automaticamente os melhores pesos em `models/weights/tennis_transformer_weights.pth`:
```bash
python train_model.py --epochs 45 --batch-size 16
```

### Passo 3.4: Executar o Sistema com o Modelo Treinado
O `pose_estimation.py` detecta e carrega automaticamente o arquivo `models/weights/tennis_transformer_weights.pth`:
```bash
# Usando a webcam:
python pose_estimation.py --source 0

# Ou testando em um vídeo gravado:
python pose_estimation.py --source dataset/raw_videos/forehand/meu_video.mp4
```
