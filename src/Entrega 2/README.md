# TennisSync - Código-Fonte e Conteúdo Físico (Entrega 2)

Este diretório contém o ambiente de desenvolvimento e base de código para a **Entrega 2** do Projeto Interdisciplinar.

---

## 📁 Estrutura da Entrega 2

```
src/Entrega 2/
├── Backend/                    # Pipeline de Visão Computacional, IA e Serviço Web Headless
│   ├── models/
│   │   ├── __init__.py
│   │   └── tennis_transformer.py
│   ├── angle_calculator.py
│   ├── extract_dataset.py
│   ├── pose_estimation.py      # Motor desacoplado TennisSyncEngine
│   ├── rule_engine.py          # Regras biomecânicas com lateralidade (US07)
│   ├── server.py               # Web Service FastAPI + WebSocket + MJPEG
│   ├── pose_landmarker_lite.task
│   ├── requirements.txt
│   └── README.md
├── IoT/                        # Hardware, Sensores e Atuadores
│   ├── firmware_leds/
│   │   └── firmware_leds.ino   # Firmware Arduino base e melhorias (pedal, voz)
│   └── README.md
└── Frontend/                   # Interface Web em React + Vite (Dashboard)
    ├── src/
    │   ├── components/         # VideoFeed, PostureHUD, AngleTelemetry, IotLedMatrix, etc.
    │   ├── hooks/              # useTennisSync com WebSocket e síntese de voz (US10)
    │   ├── services/           # mockService para simulação offline
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── README.md
```

---

## 🎯 Backlog e Objetivos da Entrega 2

Conforme especificado no Product Backlog da Proposta Técnica:

1. **US02:** Implementar filtro de suavização para eliminar jittering nas coordenadas do MediaPipe.
2. **US04:** Integrar o modelo Transformer treinado com dataset final de golpes.
3. **US05:** Desacoplar OpenCV da GPU e remover características de frontend do backend, transferindo a visualização para a aplicação Web em React.
4. **US07:** Adicionar suporte a lateralidade configurável (destro / canhoto) nas regras biomecânicas.
5. **US10:** Integrar módulo de áudio/voz para instruções corretivas sonoras.
