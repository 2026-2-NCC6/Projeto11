# Frontend - TennisSync (Entrega 1)

Na **Entrega 1**, a interface visual de feedback ao usuário é renderizada diretamente em tempo real sobre os frames de vídeo capturados via OpenCV (HUD Overlay).

- **Renderização atual:**
  - Esqueleto corporal desenhado com `mediapipe.tasks.python.vision.drawing_utils`.
  - Notificações de texto indicando golpe detectado, grau de confiança da IA e instruções corretivas na janela de exibição.
  - Indicador de FPS em tempo real.

- **Evolução planejada para Entrega 2:**
  - Desenvolvimento de dashboard dedicado / painel web para visualização de métricas, histórico de sessões e estatísticas do atleta.
