/*
 * TennisSync - Painel Fisico de Feedback Articular (IoT)
 * Disciplina: Sistemas Embarcados e Robotica / Projeto Interdisciplinar
 * Microcontrolador: Arduino Uno
 * 
 * Descricao:
 * Circuito de feedback multissensorial com 12 LEDs indicadores para articulacoes
 * corporais e um Buzzer de alerta sonoro para erros biomecanicos detectados.
 * 
 * Mapeamento de Pinos:
 * Pinos 2 a 13: 12 LEDs para indicacao de articulacoes:
 *   Porta 2  -> Ombro direito (Byte 'A')
 *   Porta 3  -> Ombro esquerdo (Byte 'B')
 *   Porta 4  -> Cotovelo direito (Byte 'C')
 *   Porta 5  -> Cotovelo esquerdo (Byte 'D')
 *   Porta 6  -> Punho direito (Byte 'E')
 *   Porta 7  -> Punho esquerdo (Byte 'F')
 *   Porta 8  -> Quadril direito (Byte 'G')
 *   Porta 9  -> Quadril esquerdo (Byte 'H')
 *   Porta 10 -> Joelho direito (Byte 'I')
 *   Porta 11 -> Joelho esquerdo (Byte 'J')
 *   Porta 12 -> Tornozelo direito (Byte 'K')
 *   Porta 13 -> Tornozelo esquerdo (Byte 'L')
 * Pino A0: Buzzer para alerta sonoro (1000 Hz por 150 ms)
 * 
 * Comando de Reset:
 *   'R' -> Desliga todos os LEDs acesos
 * 
 * Simulacao Wokwi: https://wokwi.com/projects/477109468016580609
 */

const int pinosLeds[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13};
const int totalLeds = 12;
const int buzzerPin = A0;

const char* nomesArticulacoes[] = {
  "Ombro direito",
  "Ombro esquerdo",
  "Cotovelo direito",
  "Cotovelo esquerdo",
  "Punho direito",
  "Punho esquerdo",
  "Quadril direito",
  "Quadril esquerdo",
  "Joelho direito",
  "Joelho esquerdo",
  "Tornozelo direito",
  "Tornozelo esquerdo"
};

void apagarLeds() {
  for (int i = 0; i < totalLeds; i++) {
    digitalWrite(pinosLeds[i], LOW);
  }
  Serial.println("LEDs apagados");
}

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < totalLeds; i++) {
    pinMode(pinosLeds[i], OUTPUT);
    digitalWrite(pinosLeds[i], LOW);
  }
  pinMode(buzzerPin, OUTPUT);
  Serial.println("TennisSync IoT Firmware Inicializado.");
}

void loop() {
  if (Serial.available() > 0) {
    char comando = Serial.read();

    if (comando == 'R') {
      apagarLeds();
      return;
    }

    if (comando >= 'A' && comando <= 'L') {
      int indice = comando - 'A';
      digitalWrite(pinosLeds[indice], HIGH);
      tone(buzzerPin, 1000, 150);
      Serial.print("Erro em: ");
      Serial.println(nomesArticulacoes[indice]);
    } else {
      Serial.println("Comando invalido");
    }
  }
}
