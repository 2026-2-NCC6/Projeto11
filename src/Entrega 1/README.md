# TennisSync - Código-Fonte e Conteúdo Físico (Entrega 1)

Este diretório contém todos os códigos, modelos de inteligência artificial, scripts de visão computacional e firmwares desenvolvidos para a **Entrega 1** do Projeto Interdisciplinar.

---

## 📁 Estrutura da Entrega 1

```
src/Entrega 1/
├── Backend/                    # Pipeline de Visão Computacional e Inteligência Artificial
│   ├── models/
│   │   ├── __init__.py
│   │   └── tennis_transformer.py # Classificador temporal TennisTransformerGPU (Mock)
│   ├── angle_calculator.py     # Cálculo trigonométrico de ângulos 3D (Produto Escalar)
│   ├── pose_estimation.py      # Script principal: MediaPipe, buffer, inferência e feedback
│   ├── rule_engine.py          # Motor biomecânico de regras para os golpes
│   ├── pose_landmarker_lite.task # Modelo binário de pose do MediaPipe
│   ├── requirements.txt        # Dependências do Python
│   └── README.md               # Instruções de instalação e execução do Backend
├── IoT/                        # Hardware e Sistemas Embarcados
│   ├── firmware_leds/
│   │   └── firmware_leds.ino   # Código C++ para Arduino Uno (12 LEDs + Buzzer)
│   └── README.md               # Detalhes do circuito, pinagem e link Wokwi
└── Frontend/                   # Interface com o Usuário
    └── README.md               # Explicação sobre o feedback HUD atual (OpenCV) e roadmap
```

---

## 🚀 Como Executar o Backend

1. **Instalar dependências:**
   ```bash
   cd "src/Entrega 1/Backend"
   pip install -r requirements.txt
   ```

2. **Executar o sistema:**
   ```bash
   python pose_estimation.py
   ```

---

## ⚡ Simulação do Circuito IoT

- Plataforma: [Wokwi - TennisSync Circuito](https://wokwi.com/projects/477109468016580609)
- Microcontrolador: Arduino Uno
- Taxa Serial: 9600 baud
