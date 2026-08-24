---

## 1. Visão Geral da Arquitetura Híbrida

A arquitetura do nosso sistema de análise de tênis é dividida em três camadas isoladas. Esta separação garante que não precisemos retreinar modelos complexos para adicionar novas regras de correção postural.

1.  **Camada de Extração (MediaPipe):** Processamento frame a frame do vídeo para extrair os 33 landmarks espaciais (X, Y, Z, visibilidade).
2.  **Camada de Contexto (TennisTransformerGPU):** Recebe a série temporal de landmarks, identificando janelas de tempo (início/fim do golpe) e a classe do movimento (ex: *Forehand*, *Backhand*, *Saque*).
3.  **Camada de Diagnóstico (Heurística/Geometria):** Opera exclusivamente na janela de tempo definida pela Camada 2, utilizando trigonometria para validar a biomecânica contra os ângulos ideais.

---

## 2. Fluxo de Dados e Integração (Passo a Passo)

### Passo 2.1: Estruturação do Buffer Temporizado (MediaPipe)
O `TennisTransformerGPU` não analisa frames isolados; ele requer uma sequência temporal de dados esqueléticos.

*   **Ação:** Implemente um buffer deslizante (sliding window) no output do MediaPipe.
*   **Formato de Entrada:** O tensor de entrada para o Transformer geralmente deve ter o formato `[Batch, Frames, Landmarks, Coordenadas]`. 
    *   Exemplo: Uma janela de 60 frames com 33 landmarks (X, Y, Z) resultará em um tensor de shape `(1, 60, 33, 3)`.
*   **Normalização:** Certifique-se de centralizar as coordenadas em relação a um ponto raiz (ex: o quadril - landmarks 23 e 24) para tornar a inferência invariante à posição do jogador na quadra.

### Passo 2.2: Inferência com TennisTransformerGPU
Uma vez que o buffer atinja o tamanho da janela, repasse os dados para o modelo.

```python
# Exemplo conceitual da chamada de inferência
def analisar_janela_temporal(buffer_landmarks):
    # Converter buffer para Tensor e mover para GPU
    input_tensor = torch.tensor(buffer_landmarks).to('cuda')
    
    with torch.no_grad():
        # stroke_class: ID do golpe (0=Forehand, 1=Backhand, etc.)
        # confidence: Grau de certeza da predição
        stroke_class, confidence = model_tennis_transformer(input_tensor)
        
    return stroke_class.item()
```

### Passo 2.3: Gatilho da Camada de Diagnóstico Geométrico
Quando o `TennisTransformerGPU` identificar um golpe com alta confiança (ex: `confidence > 0.85`), ele aciona o motor de regras, passando os metadados do golpe e a janela de frames correspondente.

*   **Ação:** O Agente Antigravity deve instanciar uma classe calculadora de ângulos baseada no tipo de golpe identificado.

```python
import numpy as np

def calcular_angulo(ponto_a, ponto_b, ponto_c):
    '''
    Calcula o ângulo entre três pontos 3D (ex: Ombro, Cotovelo, Pulso)
    '''
    a = np.array(ponto_a) # Ex: Ombro (Landmark 11)
    b = np.array(ponto_b) # Ex: Cotovelo (Landmark 13)
    c = np.array(ponto_c) # Ex: Pulso (Landmark 15)
    
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    
    return np.degrees(angle)
```

---

## 3. Diretrizes de Implementação para Agentes

1.  **Sincronização de Threads:** O MediaPipe é rápido (CPU), mas a inferência do Transformer (GPU) e o cálculo geométrico devem rodar em threads ou processos assíncronos distintos para não travar o FPS da leitura do vídeo.
2.  **Filtragem de Ruído:** Aplique um filtro de suavização (como Savitzky-Golay ou um Filtro de Kalman simples) nas coordenadas (X, Y, Z) extraídas pelo MediaPipe *antes* de enviá-las ao Transformer. Isso previne "saltos" (jittering) nos landmarks que derrubam a precisão do modelo.
3.  **Expansão Modular:** Para adicionar a validação de um erro novo (ex: "jogador não flexionou os joelhos no backhand"), não altere o `TennisTransformerGPU`. Apenas crie uma nova função condicional na Camada de Diagnóstico que avalie o ângulo dos landmarks 23, 25 e 27 (Quadril, Joelho, Tornozelo) sempre que o contexto for `Backhand`.

---
**Status da Integração:** Aguardando setup inicial do ambiente.