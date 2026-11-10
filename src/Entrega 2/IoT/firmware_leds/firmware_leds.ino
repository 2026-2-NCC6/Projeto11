/*
 * TennisSync - Painel Fisico de Feedback Articular (IoT)
 * Microcontrolador: Arduino Uno
 *
 * Os 12 LEDs do "corpo" sao comandados pelo backend Python (pose_estimation.py)
 * via Serial 9600 bps, 1 byte por comando. Nenhuma logica biomecanica roda aqui.
 *
 * Protocolo (identico ao MAPA_LEDS do backend):
 *   'A'..'L' -> acende o LED da articulacao correspondente (+ bip curto)
 *   'R'      -> apaga todos os LEDs
 *
 * Mapeamento de pinos (lateralidade conforme MAPA_LEDS: dir/esq do atleta):
 *   Pino 2  'A' Ombro direito        Pino 8  'G' Quadril direito
 *   Pino 3  'B' Ombro esquerdo       Pino 9  'H' Quadril esquerdo
 *   Pino 4  'C' Cotovelo direito     Pino 10 'I' Joelho direito
 *   Pino 5  'D' Cotovelo esquerdo    Pino 11 'J' Joelho esquerdo
 *   Pino 6  'E' Punho direito        Pino 12 'K' Tornozelo direito
 *   Pino 7  'F' Punho esquerdo       Pino 13 'L' Tornozelo esquerdo
 *   Pino A0: Buzzer (opcional)
 *
 * Observacao: o firmware nao envia respostas pela Serial. O backend nunca le a
 * porta (timeout=0), entao ecoar texto poderia acumular dados nao lidos.
 * Para depurar no Monitor Serial, defina DEBUG_SERIAL como 1.
 *
 * Simulacao Wokwi: https://wokwi.com/projects/477109468016580609
 */

#define DEBUG_SERIAL 0     // 1 = imprime eventos no Monitor Serial
#define USAR_BUZZER  1     // 0 = desativa o bip
#define TESTE_BOOT   1     // 1 = pisca cada LED em sequencia ao ligar

const uint8_t pinosLeds[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13};
const uint8_t totalLeds = sizeof(pinosLeds) / sizeof(pinosLeds[0]);
const uint8_t buzzerPin = A0;

#if DEBUG_SERIAL
const char* nomesArticulacoes[] = {
  "Ombro direito", "Ombro esquerdo",
  "Cotovelo direito", "Cotovelo esquerdo",
  "Punho direito", "Punho esquerdo",
  "Quadril direito", "Quadril esquerdo",
  "Joelho direito", "Joelho esquerdo",
  "Tornozelo direito", "Tornozelo esquerdo"
};
#endif

void apagarLeds() {
  for (uint8_t i = 0; i < totalLeds; i++) {
    digitalWrite(pinosLeds[i], LOW);
  }
}

void testeInicial() {
  for (uint8_t i = 0; i < totalLeds; i++) {
    digitalWrite(pinosLeds[i], HIGH);
    delay(80);
    digitalWrite(pinosLeds[i], LOW);
  }
}

void setup() {
  Serial.begin(9600);
  for (uint8_t i = 0; i < totalLeds; i++) {
    pinMode(pinosLeds[i], OUTPUT);
    digitalWrite(pinosLeds[i], LOW);
  }
#if USAR_BUZZER
  pinMode(buzzerPin, OUTPUT);
#endif
#if TESTE_BOOT
  testeInicial();
#endif
#if DEBUG_SERIAL
  Serial.println(F("TennisSync firmware pronto"));
#endif
}

void loop() {
  while (Serial.available() > 0) {
    char comando = Serial.read();

    if (comando == 'R') {
      apagarLeds();
#if DEBUG_SERIAL
      Serial.println(F("LEDs apagados"));
#endif
    } else if (comando >= 'A' && comando <= 'L') {
      uint8_t indice = comando - 'A';
      // So bipa na transicao apagado -> aceso (backend reenvia o byte por frame)
      bool jaAceso = digitalRead(pinosLeds[indice]) == HIGH;
      digitalWrite(pinosLeds[indice], HIGH);
#if USAR_BUZZER
      if (!jaAceso) tone(buzzerPin, 1000, 150);
#endif
#if DEBUG_SERIAL
      Serial.print(F("Erro em: "));
      Serial.println(nomesArticulacoes[indice]);
#endif
    }
    // Demais bytes (ex.: \r, \n) sao ignorados.
  }
}
