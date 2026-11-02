# IoT e Sistemas Embarcados - TennisSync (Entrega 1)

Este diretório contém o firmware desenvolvido para o painel de feedback físico do TennisSync, utilizando Arduino Uno, 12 LEDs indicadores e um Buzzer de alerta sonoro.

---

## 📌 Mapeamento de Articulações e Portas

| Byte Serial | Articulação | Pino Arduino Uno | Cor Típica |
|:---:|:---|:---:|:---:|
| `A` | Ombro direito | 2 | Vermelho |
| `B` | Ombro esquerdo | 3 | Vermelho |
| `C` | Cotovelo direito | 4 | Azul |
| `D` | Cotovelo esquerdo | 5 | Azul |
| `E` | Punho direito | 6 | Verde |
| `F` | Punho esquerdo | 7 | Verde |
| `G` | Quadril direito | 8 | Amarelo |
| `H` | Quadril esquerdo | 9 | Amarelo |
| `I` | Joelho direito | 10 | Branco |
| `J` | Joelho esquerdo | 11 | Branco |
| `K` | Tornozelo direito | 12 | Verde |
| `L` | Tornozelo esquerdo | 13 | Verde |
| - | Buzzer (Alerta Sonoro) | A0 | - |
| `R` | Comando de Reset (Apagar LEDs) | N/A | - |

---

## 🌐 Simulação Interativa no Wokwi

O circuito foi completamente prototipado e testado no simulador Wokwi:
- **Link do projeto:** [Wokwi TennisSync Circuit](https://wokwi.com/projects/477109468016580609)
