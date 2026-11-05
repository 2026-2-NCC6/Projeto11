# Backend - TenniSync (Entrega 2)

Ambiente de código do Backend para o ciclo de desenvolvimento da **Entrega 2**, incluindo o pipeline de Visão Computacional, IA (`TennisTransformerGPU`), Motor de Regras Biomecânicas e **Serviço Web Desacoplado** (FastAPI / WebSocket).

> ⚠️ **Arquitetura Desacoplada (Entrega 2):**  
> Todas as características de frontend (janelas `cv2.imshow`, overlays de texto `cv2.putText` e HUD local) foram removidas da execução padrão do Backend e migradas para a aplicação Web em **React** localizada em `Frontend/`. O backend agora opera como um Web Service assíncrono headless que transmite telemetria via WebSocket e vídeo via MJPEG.

---

## 📁 Estrutura de Arquivos

```text
Backend/
├── dataset/
│   ├── raw_videos/                 # Vídeos brutos organizados por golpe
│   ├── processed/                  # Datasets processados (.npz)
│   └── README.md                   # Guia de gravação e treinamento
├── models/
│   ├── weights/                    # Pesos treinados (.pth)
│   ├── __init__.py
│   └── tennis_transformer.py       # Modelo Transformer PyTorch
├── angle_calculator.py             # Trigonometria 3D de ângulos articulares
├── extract_dataset.py              # Extrator de séries temporais esqueléticas
├── gamification_engine.py          # Motor de Gamificação, Modo Rally, Vidas, Pontos e XP
├── hud_renderer.py                 # Renderizador de HUD visual arcade para OpenCV
├── pose_estimation.py              # Classe TennisSyncEngine híbrida (standalone + headless)
├── record_training_videos.py       # Utilitário para gravação de amostras
├── rule_engine.py                  # Motor biomecânico com suporte a lateralidade e notas
├── server.py                       # Serviço Web FastAPI + WebSocket para o Frontend React
├── tests/                          # Testes unitários automatizados
│   └── test_gamification.py        # Suíte de testes da gamificação e biomecânica
├── train_model.py                  # Script de treinamento supervisionado
├── pose_landmarker_lite.task       # Modelo MediaPipe Pose
└── requirements.txt                # Dependências (incluindo fastapi, uvicorn, websockets)
```

---

## ▶️ Inicialização do Serviço Web

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Iniciar o Serviço Web da API
```bash
python server.py
# ou alternativamente:
uvicorn server:app --host 0.0.0.0 --port 8000
```
O serviço disponibilizará:
- `http://localhost:8000/api/status` - Status do motor, câmera e hardware IoT
- `http://localhost:8000/api/video_feed` - Stream MJPEG em tempo real
- `ws://localhost:8000/ws/telemetry` - WebSocket com eventos de telemetria e classificação
- `http://localhost:8000/docs` - Documentação interativa Swagger/OpenAPI

### 3. Execução do Modo Jogo Arcade em OpenCV (Híbrido)
Caso queira executar a experiência interativa completa diretamente com a janela de vídeo e a nova HUD arcade em tempo real:
```bash
python pose_estimation.py --source 0 --lateralidade destro
```
- Pressione **'R'** para reiniciar o Rally.
- Pressione **'Q'** para encerrar e exportar o histórico da sessão para `data/session_history.json`.

### 4. Executar os Testes Automatizados da Gamificação
```bash
python -m unittest tests/test_gamification.py -v
```
