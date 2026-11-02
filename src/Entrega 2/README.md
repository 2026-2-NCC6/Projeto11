# TennisSync - Código-Fonte e Conteúdo Físico (Entrega 2)

Este diretório contém o ambiente de desenvolvimento e base de código para a **Entrega 2** do Projeto Interdisciplinar.

---

## 📁 Estrutura da Entrega 2

```
src/Entrega 2/
├── Backend/                    # Pipeline de Visão Computacional, IA e novos módulos
│   ├── models/
│   │   ├── __init__.py
│   │   └── tennis_transformer.py
│   ├── angle_calculator.py
│   ├── pose_estimation.py
│   ├── rule_engine.py
│   ├── pose_landmarker_lite.task
│   ├── requirements.txt
│   └── README.md               # Detalhes das metas e melhorias da Entrega 2
├── IoT/                        # Hardware, Sensores e Atuadores
│   ├── firmware_leds/
│   │   └── firmware_leds.ino   # Firmware Arduino base e melhorias (pedal, voz)
│   └── README.md
└── Frontend/                   # Interface gráfica / Dashboard
    └── README.md               # Planejamento da interface da Entrega 2
```

---

## 🎯 Backlog e Objetivos da Entrega 2

Conforme especificado no Product Backlog da Proposta Técnica:

1. **US02:** Implementar filtro de suavização (Savitzky-Golay / Kalman simples) para eliminar jittering nas coordenadas do MediaPipe.
2. **US04:** Integrar o modelo Transformer treinado com dataset final de golpes.
3. **US05:** Desacoplar OpenCV da GPU através de multi-threading assíncrono para manter FPS estável.
4. **US07:** Adicionar suporte a lateralidade configurável (destro / canhoto) nas regras biomecânicas.
5. **US10:** Integrar módulo de áudio/voz para instruções corretivas sonoras.
