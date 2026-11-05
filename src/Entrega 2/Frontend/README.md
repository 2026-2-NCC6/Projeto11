# Frontend - TenniSync (Entrega 2)

Interface Web moderna em **React + Vite** construída para o serviço web do **TenniSync**.

Nesta **Entrega 2**, as características visuais e de interação com o usuário foram **completamente removidas do Backend (OpenCV HUD)** e transferidas para esta aplicação Web dedicada, estabelecendo uma arquitetura desacoplada e modular.

---

## 🚀 Funcionalidades da Interface

1. **Feed Visual do Atleta:**
   - Reprodução em tempo real do stream de vídeo do backend via endpoint MJPEG (`/api/video_feed`).
   - Opção de visualização via **Câmera Local do Navegador** ou animação sintética de esqueleto esportivo.
   - Indicador de FPS dinâmico e status do pipeline.

2. **HUD de Postura & Classificação IA:**
   - Exibição do golpe atual classificado pelo modelo Transformer (*Forehand*, *Backhand*, *Saque*, *Repouso*) com percentual de confiança.
   - Parecer biomecânico imediato (*Aprovado* vs *Desvio Detectado*).
   - Destaque das articulações que violaram os limites angulares ideais.

3. **Telemetria de Ângulos 3D (Trigonometria):**
   - Medidores angulares em tempo real para Cotovelos (D/E) e Joelhos (D/E).
   - Barras de progresso com faixas de conformidade biomecânica.

4. **Matriz Virtual IoT / Arduino (12 LEDs):**
   - Espelhamento em tempo real do painel de hardware (Portas 2 a 13 do Arduino / Bytes `'A'` a `'L'` e Reset `'R'`).
   - Acendimento visual das lâmpadas virtuais mapeadas diretamente nas articulações correspondentes.

5. **Controles de Sessão e Configuração:**
   - **Lateralidade configurável (US07):** Alternância instantânea entre tenista *Destro* e *Canhoto*.
   - **Instruções de Voz (US10):** Síntese de voz em português via Web Speech API anunciando correções posturais.
   - Iniciar, pausar e resetar contadores e cronômetro de sessão.

6. **Relatórios e Histórico da Sessão:**
   - Taxa de acurácia postural (%) acumulada.
   - Contagem segmentada por golpe (*Forehands*, *Backhands*, *Saques*).
   - Log cronológico dos movimentos com filtro (*Todos*, *Aprovados*, *Correções*) e botão de exportação em JSON.

7. **Gamificação & Modo Rally Virtual:**
   - Contador de rebatidas consecutivas de Rally com indicação de recorde.
   - Sistema de vidas (3 corações) com perda em desvios posturais e tela de Game Over.
   - Pontuação dinâmica com multiplicadores de combo (1.0x a 3.0x).
   - Sistema de XP e Patentes de Tênis (*Iniciante* a *Grand Slam Master*).
   - Feedback de qualidade instantâneo (*PERFECT*, *GOOD*, *FAULT*).
   - Botão de reinício de Rally com sincronia bidirecional via WebSocket e API.

---

## 🛠️ Como Executar

### 1. Instalar Dependências (se ainda não instaladas)
```bash
npm install
```

### 2. Iniciar o Servidor de Desenvolvimento
```bash
npm run dev
```
Acesse a aplicação no seu navegador em: `http://localhost:3000`

### 3. Gerar Build de Produção
```bash
npm run build
```

---

## 🔄 Comunicação com o Backend

A interface conecta-se automaticamente ao backend:
- **WebSocket:** `ws://localhost:8000/ws/telemetry` (para telemetria de 30 FPS, troca de configurações e eventos).
- **Stream de Vídeo:** `http://localhost:8000/api/video_feed` (MJPEG limpo).
- **Modo Offline/Demonstração:** Caso o backend Python não esteja rodando, a interface aciona automaticamente um gerador de telemetria simulada para testes e avaliação visual completa.
