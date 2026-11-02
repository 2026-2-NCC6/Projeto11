# FECAP - Fundação de Comércio Álvares Penteado

<p align="center">
<a href="https://www.fecap.br/"><img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRhZPrRa89Kma0ZZogxm0pi-tCn_TLKeHGVxywp-LXAFGR3B1DPouAJYHgKZGV0XTEf4AE&usqp=CAU" alt="FECAP - Fundação de Comércio Álvares Penteado" border="0"></a>
</p>

# TennisSync

## Equipe: TennisSync (Ciência da Computação - 6º Semestre)

## Integrantes: <a href="https://www.linkedin.com/in/bernardoseijascavalcante/">Bernardo Seijas Cavalcante</a>, <a href="https://github.com/carlinhoslatorre">Carlos Roberto Santos Latorre</a>, <a href="https://www.linkedin.com/in/felipe-wakasa-76a93a257/">Felipe Wakasa Klabunde</a>, <a href="https://www.linkedin.com/in/stephany-aliyah-4a2589321/">Stephany Aliyah Guimarães Eurípedes de Paula</a>

## Professores Orientadores: <a href="https://www.linkedin.com/in/trencher/">João Francisco Trencher Martins</a>, <a href="https://www.linkedin.com/in/professorrodnil/">Rodnil da Silva Moreira Lisboa</a>, <a href="https://www.linkedin.com/in/victorbarq/">Victor Bruno Alexander Rosetti de Quiroz</a>, <a href="https://www.linkedin.com/in/edsonbarbero/">Edson Ricardo Barbero</a>, <a href="https://www.linkedin.com/in/katia-bossi/">Kátia Milani Lara Bossi</a>

## 📝 Descrição

O **TennisSync** é um sistema de análise biomecânica em tempo real e treinador interativo para jogadores de tênis. O projeto utiliza visão computacional, inteligência artificial e Internet das Coisas (IoT) para automatizar o diagnóstico postural durante os treinamentos.

O sistema opera através de uma arquitetura modular de três camadas:
1. **Camada de Extração:** Rastreamento do atleta via câmera com extração de 33 landmarks espaciais 3D (X, Y, Z) utilizando o MediaPipe Pose Landmarker, normalizados em relação ao centro do quadril.
2. **Camada de Contexto:** Classificador temporal (Transformer) que processa janelas deslizantes de 60 frames para identificar a classe do golpe executado (*Forehand*, *Backhand*, *Saque* ou *Repouso*).
3. **Camada de Diagnóstico:** Motor geométrico heurístico que valida os ângulos articulares através do cálculo do produto escalar de vetores 3D, comparando-os com limiares biomecânicos.

O feedback multissensorial é emitido em tempo real:
- **Visual (HUD):** Texto e esqueleto sobrepostos ao vídeo (OpenCV).
- **Físico (IoT):** Painel de 12 LEDs no Arduino Uno mapeando as articulações com desvios posturais.
- **Sonoro:** Buzzer no circuito e módulo de voz corretiva.

---

## 🛠 Estrutura de Pastas

```
Projeto11/
├── documentos/                         # Documentação acadêmica e técnica do projeto
│   ├── Entrega 1/                      # Relatórios da Entrega 1 por disciplina
│   │   ├── Inovação e Empreendedorismo/
│   │   ├── Projeto Interdisciplinar - Internet das Coisas e Robótica/
│   │   ├── Redes de Computadores e Cibersegurança/
│   │   ├── Sistemas Embarcados e Robótica/
│   │   └── Teoria da Computação e Linguagens Formais/
│   ├── Entrega 2/                      # Documentação em desenvolvimento da Entrega 2
│   ├── arquitetura_sistema.md          # Especificação da arquitetura híbrida de 3 camadas
│   └── integracao_iot.md               # Especificação da integração serial com o Arduino
├── imagens/                            # Recursos visuais e diagramas
├── src/                                # Conteúdo físico do projeto (Códigos-fonte e Firmwares)
│   ├── Entrega 1/                      # Versão final homologada da Entrega 1
│   │   ├── Backend/                    # Pipeline de Visão Computacional, IA e Regras
│   │   │   ├── models/                 # TennisTransformerGPU
│   │   │   ├── angle_calculator.py     # Trigonometria 3D de ângulos articulares
│   │   │   ├── pose_estimation.py      # Script principal do pipeline
│   │   │   ├── rule_engine.py          # Validação biomecânica dos golpes
│   │   │   ├── pose_landmarker_lite.task # Modelo MediaPipe
│   │   │   └── requirements.txt
│   │   ├── IoT/                        # Hardware e Firmware Embarcado
│   │   │   └── firmware_leds/          # Código C++ (.ino) para Arduino Uno
│   │   └── Frontend/                   # Interface visual (HUD OpenCV)
│   └── Entrega 2/                      # Ambiente de desenvolvimento da Entrega 2
│       ├── Backend/                    # Base de código para melhorias da Entrega 2
│       ├── IoT/                        # Firmware para suporte a pedal e voz
│       └── Frontend/                   # Estrutura para dashboard web
├── .gitignore                          # Regras de exclusão do Git (Python, Node, OS)
└── README.md                           # Guia geral do projeto
```

---

## 💻 Instalação e Execução

### Pré-requisitos
- Python 3.10 ou superior
- Webcam conectada
- (Opcional) Arduino Uno com o firmware gravado na porta Serial `COM4`

### Passos de Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/fecaphub/Projeto11.git
   ```

2. Acesse o diretório do Backend:
   ```bash
   cd "src/Entrega 1/Backend"
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Execute o sistema:
   ```bash
   python pose_estimation.py
   ```

---

## ⚡ Simulação do Circuito IoT

- Plataforma Wokwi: [Circuito TennisSync no Wokwi](https://wokwi.com/projects/477109468016580609)
- Firmware Arduino: `src/Entrega 1/IoT/firmware_leds/firmware_leds.ino`
