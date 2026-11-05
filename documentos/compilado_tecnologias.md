# 🎾 Compilado de Tecnologias — TennisSync (FECAP)

Este documento reúne todas as **tecnologias, frameworks, bibliotecas e plataformas de hardware** empregadas no desenvolvimento do ecossistema **TennisSync** (Englobando a Entrega 1 e Entrega 2 do Projeto Interdisciplinar).

Todos os logotipos oficiais foram baixados e encontram-se salvos no repositório em:  
📁 `imagens/tecnologias/` (prontos para inserção em relatórios Word, PDFs ou no Banner da FECAP).

---

## 🧠 1. Visão Computacional, Inteligência Artificial e Biomecânica

| Tecnologia | Logotipo | Camada / Função no TennisSync |
| :--- | :---: | :--- |
| **Google MediaPipe** | <img src="https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/mediapipe.svg" width="60" height="60" alt="MediaPipe"/> | **Camada 1 (Extração):** Modelo *Pose Landmarker* responsável pelo rastreamento esquelético 3D de alta performance em tempo real, extraindo os 33 marcos anatômicos com coordenadas normalizadas em relação ao quadril. |
| **PyTorch** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/pytorch/pytorch-original.svg" width="60" height="60" alt="PyTorch"/> | **Camada 2 (Contexto):** Framework de Deep Learning que executa a arquitetura `TennisTransformerGPU`, processando janelas deslizantes temporais de 60 frames para classificar os golpes de tênis (*Forehand*, *Backhand*, *Saque* e *Repouso*). |
| **OpenCV** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/opencv/opencv-original.svg" width="60" height="60" alt="OpenCV"/> | **Visão Computacional & Vídeo:** Captura do stream da webcam em alta taxa de quadros, pré-processamento de imagens, desenho das linhas de articulações (HUD visual) e geração do streaming MJPEG. |
| **NumPy** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/numpy/numpy-original.svg" width="60" height="60" alt="NumPy"/> | **Camada 3 (Diagnóstico):** Cálculo vetorial 3D contínuo (produto escalar e norma de vetores euclidianos) para mensuração dos ângulos anatômicos das articulações e validação das regras biomecânicas. |

---

## ⚡ 2. Backend, Web Service e Telemetria em Tempo Real

| Tecnologia | Logotipo | Função no TennisSync |
| :--- | :---: | :--- |
| **Python 3.10+** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" width="60" height="60" alt="Python"/> | **Linguagem Principal:** Linguagem base de desenvolvimento de todo o pipeline de IA, motor de inferência, regras de postura e servidor web assíncrono. |
| **FastAPI** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/fastapi/fastapi-original.svg" width="60" height="60" alt="FastAPI"/> | **API Web Assíncrona:** Gerenciamento dos endpoints REST, streaming HTTP MJPEG da câmera e orquestração do ciclo de vida das sessões de treino (Entrega 2). |
| **Uvicorn** | <img src="https://raw.githubusercontent.com/encode/uvicorn/master/docs/uvicorn.png" width="60" height="60" alt="Uvicorn"/> | **Servidor ASGI:** Servidor de aplicações assíncronas de ultrabaixa latência para execução do FastAPI com suporte a concorrência e WebSockets. |
| **WebSockets** | <img src="https://raw.githubusercontent.com/gilbarbara/logos/master/logos/websocket.svg" width="60" height="60" alt="WebSocket"/> | **Comunicação Bidirecional:** Protocolo full-duplex de baixa latência transmitindo telemetria esquelética, métricas angulares e diagnósticos posturais a 30+ FPS do Backend para o Frontend. |

---

## 💻 3. Frontend e Interface do Usuário (Dashboard Reativo)

| Tecnologia | Logotipo | Função no TennisSync |
| :--- | :---: | :--- |
| **React 18** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/react/react-original.svg" width="60" height="60" alt="React"/> | **Interface do Usuário:** Biblioteca para construção do Dashboard reativo, painéis de telemetria em tempo real, HUD virtual e matriz visual de 12 LEDs. |
| **Vite** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/vitejs/vitejs-original.svg" width="60" height="60" alt="Vite"/> | **Build Tool & Bundler:** Ambiente de empacotamento ultrarrápido com Hot Module Replacement (HMR) para agilidade no desenvolvimento front-end. |
| **Tailwind CSS** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/tailwindcss/tailwindcss-original.svg" width="60" height="60" alt="Tailwind CSS"/> | **Design System & Estilização:** Framework de estilização utilitária para estética esportiva com tema escuro (Dark Mode), painéis translúcidos e indicadores visuais de alto contraste. |
| **Lucide Icons** | <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/activity.svg" width="60" height="60" alt="Lucide"/> | **Iconografia Vetorial:** Conjunto de ícones leves aplicados na telemetria, indicadores de status corporal, conectividade de hardware e controles da câmera. |
| **Web Speech API** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/html5/html5-original.svg" width="60" height="60" alt="Web Speech"/> | **Instruções por Voz (US10):** Síntese vocal nativa do navegador que reproduz orientações corretivas audíveis para o tenista sem necessidade de olhar para a tela. |

---

## 🔌 4. Sistemas Embarcados, IoT e Hardware

| Tecnologia | Logotipo | Função no TennisSync |
| :--- | :---: | :--- |
| **Arduino Uno** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/arduino/arduino-original.svg" width="60" height="60" alt="Arduino"/> | **Microcontrolador Físico:** Placa embarcada controlando 12 LEDs indicadores anatômicos (ombros, cotovelos, quadris, joelhos e tornozelos), buzzer sonoro e sensor de pedal de acionamento. |
| **C / C++** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/cplusplus/cplusplus-original.svg" width="60" height="60" alt="C++"/> | **Firmware Embarcado:** Linguagem do código-fonte compilado no microcontrolador (`firmware_leds.ino`), implementando decodificação de bytes seriais e acionamento por registradores digitais. |
| **Wokwi** | <img src="https://avatars.githubusercontent.com/u/74640103?s=200&v=4" width="60" height="60" alt="Wokwi"/> | **Simulação Virtual de Circuitos:** Plataforma de prototipagem em nuvem que permitiu simular o circuito elétrico completo com LEDs, resistores e buzzer antes da montagem na bancada. |
| **PySerial** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" width="60" height="60" alt="PySerial"/> | **Comunicação Serial UART:** Módulo Python responsável por enviar comandos via porta COM (`COM3`/`COM4`) com taxa de 9600 baud rate, sincronizando a IA com os LEDs físicos. |

---

## 🛠️ 5. Versionamento e Governança Acadêmica

| Tecnologia | Logotipo | Função no TennisSync |
| :--- | :---: | :--- |
| **Git** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/git/git-original.svg" width="60" height="60" alt="Git"/> | **Controle de Versão:** Rastreamento do histórico de alterações, branches de entrega e versionamento do código entre as disciplinas. |
| **GitHub** | <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/github/github-original.svg" width="60" height="60" alt="GitHub"/> | **Repositório Central:** Hospedagem remota oficial do projeto sob a organização da faculdade (`fecaphub/Projeto11`), com documentações e relatórios técnicos. |

---

## 📁 Galeria de Arquivos Locais no Repositório

Os arquivos foram baixados e estruturados em `imagens/tecnologias/`:

```
imagens/tecnologias/
├── arduino.svg
├── cplusplus.svg
├── fastapi.svg
├── git.svg
├── github.svg
├── lucide.svg
├── mediapipe.png
├── mediapipe.svg
├── numpy.svg
├── opencv.svg
├── python.svg
├── pytorch.svg
├── react.svg
├── tailwindcss.svg
├── uvicorn.png
├── vite.svg
├── websocket.svg
└── wokwi.png
```
