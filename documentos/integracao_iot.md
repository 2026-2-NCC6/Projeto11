# Integração do Painel de Feedback (Arduino) com a Arquitetura Principal

**Objetivo:** Integrar o sistema de alertas visuais físicos (12 LEDs) à Camada de Diagnóstico Geométrico do nosso pipeline de análise biomecânica, permitindo que a infraestrutura indique em tempo real qual ponto articular apresentou desvio postural.

---

## 1. Topologia de Hardware e Portas
Utilizaremos 12 pinos digitais no Arduino (Portas de 2 a 13). Cada porta mapeia um dos 12 landmarks principais do MediaPipe que englobam membros superiores e inferiores, omitindo extremidades (mãos/pés) e face.

| Landmark (MediaPipe) | Parte do Corpo | Porta (Arduino) | Byte de Comando |
| :--- | :--- | :--- | :--- |
| 11 | Ombro Esquerdo | 2 | `A` |
| 12 | Ombro Direito | 3 | `B` |
| 13 | Cotovelo Esquerdo | 4 | `C` |
| 14 | Cotovelo Direito | 5 | `D` |
| 15 | Pulso Esquerdo | 6 | `E` |
| 16 | Pulso Direito | 7 | `F` |
| 23 | Quadril Esquerdo | 8 | `G` |
| 24 | Quadril Direito | 9 | `H` |
| 25 | Joelho Esquerdo | 10 | `I` |
| 26 | Joelho Direito | 11 | `J` |
| 27 | Tornozelo Esquerdo| 12 | `K` |
| 28 | Tornozelo Direito | 13 | `L` |
| N/A | Reset (Limpar Alertas)| N/A | `R` |

---

## 2. Implementação no Microcontrolador (Arduino)
O firmware do Arduino deve ser focado puramente em recepção Serial. Nenhuma lógica de validação biomecânica rodará na placa.

**Código C++ (`firmware_leds.ino`):**
```cpp
const int pinosLeds[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13};
const int totalLeds = 12;

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < totalLeds; i++) {
    pinMode(pinosLeds[i], OUTPUT);
  }
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();

    if (comando == 'R') {
      for (int i = 0; i < totalLeds; i++) { digitalWrite(pinosLeds[i], LOW); }
      return; 
    }

    if (comando >= 'A' && comando <= 'L') {
      int indice = comando - 'A'; // Traduz char ASCII para índice do array (0 a 11)
      digitalWrite(pinosLeds[indice], HIGH);
    }
  }
}
```

---

## 3. Integração na Camada de Diagnóstico (Python)
A comunicação serial deve ser instanciada no início do script principal e acionada pelos gatilhos das regras matemáticas.

**Adições ao Código Principal:**

1.  **Inicialização:**
    Instancie a conexão serial globalmente antes do loop de captura de vídeo para evitar reinicialização na porta.
    ```python
    import serial
    
    # ATENÇÃO: Atualizar a porta COM para o ambiente de execução local
    try:
        feedback_arduino = serial.Serial('COM3', 9600, timeout=0)
    except:
        feedback_arduino = None
        print("Aviso: Painel de LEDs desconectado.")
    ```

2.  **Mapeamento Constante:**
    Adicione o dicionário de tradução na raiz do módulo.
    ```python
    MAPA_LEDS = {
        "ombro_esq": b'A', "ombro_dir": b'B', "cotovelo_esq": b'C', 
        "cotovelo_dir": b'D', "pulso_esq": b'E', "pulso_dir": b'F',
        "quadril_esq": b'G', "quadril_dir": b'H', "joelho_esq": b'I', 
        "joelho_dir": b'J', "tornozelo_esq": b'K', "tornozelo_dir": b'L'
    }
    ```

3.  **Implementação do Gatilho:**
    Dentro da sua função de validação de regras (após receber a classe do golpe do `TennisTransformerGPU`), implemente os disparos condicionais.
    ```python
    def validar_postura(angulos_calculados, tipo_golpe):
        # ... lógica de validação ...
        
        # Exemplo: Se falhou na validação de base do Backhand
        if erro_joelho:
            feedback_arduino.write(MAPA_LEDS["joelho_dir"])
            
        # Quando o movimento for finalizado/corrigido
        if movimento_correto:
            feedback_arduino.write(b'R')
    ```

## 4. Contenção de Gargalos (Crucial)
Devido ao alto framerate de inferência e ao buffer do Transformer, evite enviar o mesmo comando (ex: `b'C'`) repetidamente frame após frame. Implemente um controle de estado (variável booleana) no Python para garantir que o byte seja enviado apenas *uma vez* quando o erro for detectado e o comando de reset (`b'R'`) apenas *uma vez* quando o movimento voltar ao limite aceitável.