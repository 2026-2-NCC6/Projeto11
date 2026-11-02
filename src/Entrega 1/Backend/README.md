# Backend - TennisSync (Entrega 1)

O módulo de Backend implementa o núcleo computacional do TennisSync, baseado em uma arquitetura híbrida de três camadas:

1. **Camada de Extração:** MediaPipe Pose Landmarker extrai 33 landmarks espaciais (x, y, z) e centraliza-os nas coordenadas do quadril.
2. **Camada de Contexto:** `TennisTransformerGPU` processa uma janela temporal de 60 frames para prever o golpe (Forehand, Backhand, Saque).
3. **Camada de Diagnóstico:** `rule_engine` e `angle_calculator` utilizam produto escalar de vetores 3D para diagnosticar desvios posturais.

---

## 🛠 Requisitos e Instalação

Recomenda-se o uso de Python 3.10 ou superior.

```bash
pip install -r requirements.txt
```

---

## ▶️ Execução

Para iniciar o rastreamento via webcam e análise biomecânica:

```bash
python pose_estimation.py
```

- Pressione **'q'** na janela de vídeo para encerrar a execução.
- Para integrar com o painel físico Arduino, conecte-o via USB (ajuste a porta COM no código, se necessário). O sistema possui tolerância a falhas e continuará funcionando no modo puramente visual se a porta serial não estiver disponível.
