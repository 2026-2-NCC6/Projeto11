# Backend - TennisSync (Entrega 2)

Ambiente de código do Backend para o ciclo de desenvolvimento da **Entrega 2**, incluindo o pipeline completo de coleta de vídeos, extração de landmarks 3D e treinamento do modelo `TennisTransformerGPU`.

---

## 📁 Estrutura de Arquivos

```text
Backend/
├── dataset/
│   ├── raw_videos/
│   │   ├── forehand/               # Vídeos brutos de Forehand (Classe 0)
│   │   ├── backhand/               # Vídeos brutos de Backhand (Classe 1)
│   │   ├── saque/                  # Vídeos brutos de Saque (Classe 2)
│   │   └── repouso/                # Vídeos brutos de Repouso/Espera (Classe 3)
│   ├── processed/                  # Datasets processados (.npz)
│   └── README.md                   # Guia detalhado de gravação e treinamento
├── models/
│   ├── weights/                    # Pesos treinados (.pth) carregados automaticamente
│   ├── __init__.py
│   └── tennis_transformer.py       # Arquitetura PyTorch TennisTransformerNet + Wrapper GPU/CPU
├── angle_calculator.py             # Trigonometria 3D de ângulos articulares
├── extract_dataset.py              # Extrator de janelas (60, 33, 3) a partir dos vídeos
├── pose_estimation.py              # Pipeline principal de inferência em tempo real
├── record_training_videos.py       # Utilitário para gravar vídeos rotulados via webcam
├── rule_engine.py                  # Motor biomecânico de avaliação postural
├── train_model.py                  # Script de treinamento supervisionado em PyTorch
├── pose_landmarker_lite.task       # Modelo MediaPipe Pose
└── requirements.txt                # Dependências do projeto
```

---

## ▶️ Fluxo Completo de Uso

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Adicionar ou Gravar Vídeos de Treinamento
Coloque seus vídeos nas pastas `dataset/raw_videos/{forehand,backhand,saque,repouso}` ou grave pela webcam:
```bash
python record_training_videos.py --camera 0
```

### 3. Extrair Landmarks e Gerar Dataset (`.npz`)
```bash
python extract_dataset.py --augment-mirror
```

### 4. Treinar o Modelo (`TennisTransformerGPU`)
```bash
python train_model.py --epochs 45
```

### 5. Executar o Diagnóstico em Tempo Real
```bash
python pose_estimation.py --source 0
```
