from camera_utils import get_usb_camera_source, is_camera_blacklisted
import os
import sys
import time
import argparse
import threading
import cv2
import numpy as np

try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEST_DIR = os.path.join(BASE_DIR, "dataset", "raw_videos", "repouso_50")
os.makedirs(DEST_DIR, exist_ok=True)

# Conexões anatômicas do esqueleto MediaPipe Pose (33 marcos)
POSE_CONNECTIONS = [
    # Face
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    # Ombros e Tronco
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Braço Esquerdo
    (11, 13), (13, 15), (15, 17), (15, 19), (15, 21),
    # Braço Direito
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22),
    # Perna Esquerda
    (23, 25), (25, 27), (27, 29), (29, 31),
    # Perna Direita
    (24, 26), (26, 28), (28, 30), (30, 32)
]

# Catálogo completo e detalhado dos 50 vídeos de repouso estruturado em 5 lotes temáticos
CATALOG = [
    # LOTE A: Posturas Estáticas & Respiração (01 a 10)
    {
        "idx": 1,
        "fname": "repouso_01_estatico_corpo_inteiro",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "EM PÉ RELAXADO (CORPO INTEIRO)",
        "dist": "3.5m (Corpo Inteiro - Pés à Cabeça)",
        "postura": "Pés na largura dos ombros, ereto, braços soltos ao lado",
        "acao": "Fique estático respirando normalmente pelos 12s"
    },
    {
        "idx": 2,
        "fname": "repouso_02_estatico_media_distancia",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "EM PÉ RELAXADO (MÉDIA DISTÂNCIA)",
        "dist": "2.5m (Média Distância - Canela à Cabeça)",
        "postura": "Dê 1 passo à frente, pés firmes, postura ereta e relaxada",
        "acao": "Braços caídos ao lado do corpo, estático sem golpear"
    },
    {
        "idx": 3,
        "fname": "repouso_03_estatico_joelhos_cima",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "EM PÉ RELAXADO (JOELHOS PARA CIMA)",
        "dist": "2.0m (Joelhos para cima até a Cabeça)",
        "postura": "Mais 1 passo à frente, enquadrando cintura/joelhos até cabeça",
        "acao": "Ombros e braços soltos, totalmente em repouso"
    },
    {
        "idx": 4,
        "fname": "repouso_04_peso_perna_direita",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "APOIO DE PESO NA PERNA DIREITA",
        "dist": "2.5m a 3.5m (Visão Geral)",
        "postura": "Descanse o peso do corpo sobre a perna direita",
        "acao": "Perna esquerda relaxada (postura casual de espera)"
    },
    {
        "idx": 5,
        "fname": "repouso_05_peso_perna_esquerda",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "APOIO DE PESO NA PERNA ESQUERDA",
        "dist": "2.5m a 3.5m (Visão Geral)",
        "postura": "Descanse o peso do corpo sobre a perna esquerda",
        "acao": "Perna direita relaxada (postura casual de espera)"
    },
    {
        "idx": 6,
        "fname": "repouso_06_respiracao_profunda",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "RESPIRAÇÃO PROFUNDA & SWAY",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé ereto, ombros relaxados",
        "acao": "Inspire e expire profundamente inflando o tórax, braços inertes"
    },
    {
        "idx": 7,
        "fname": "repouso_07_perfil_45_esquerda",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "PERFIL 45 GRAUS PARA A ESQUERDA",
        "dist": "2.5m a 3.5m",
        "postura": "Gire o corpo 45° apontando para o seu lado esquerdo",
        "acao": "Mantenha a postura diagonal relaxada, olhando para frente"
    },
    {
        "idx": 8,
        "fname": "repouso_08_perfil_45_direita",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "PERFIL 45 GRAUS PARA A DIREITA",
        "dist": "2.5m a 3.5m",
        "postura": "Gire o corpo 45° apontando para o seu lado direito",
        "acao": "Mantenha a postura diagonal relaxada, olhando para frente"
    },
    {
        "idx": 9,
        "fname": "repouso_09_costas_para_camera",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "DE COSTAS PARA A CÂMERA",
        "dist": "2.5m a 3.5m",
        "postura": "Fique totalmente de costas para a câmera",
        "acao": "Postura ereta de espera de saque no fundo de quadra"
    },
    {
        "idx": 10,
        "fname": "repouso_10_maos_cruzadas_cintura",
        "lote": "LOTE A: POSTURAS ESTÁTICAS & RESPIRAÇÃO",
        "title": "MÃOS CRUZADAS NA CINTURA / QUADRIL",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé de frente para a câmera",
        "acao": "Cruze ou repouse ambas as mãos na frente do quadril/cintura"
    },

    # LOTE B: Posição de Prontidão do Tênis / Ready Position (11 a 20)
    {
        "idx": 11,
        "fname": "repouso_11_ready_stance_corpo_inteiro",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE CLÁSSICO (CORPO INTEIRO)",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Joelhos flexionados, tronco levemente inclinado à frente",
        "acao": "Mãos juntas na frente segurando raquete/cabo na altura da cintura"
    },
    {
        "idx": 12,
        "fname": "repouso_12_ready_stance_media_dist",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE (MÉDIA DISTÂNCIA)",
        "dist": "2.5m (Média Distância)",
        "postura": "Dê 1 passo à frente, base atlética de tênis",
        "acao": "Joelhos semi-flexionados, raquete na frente do tronco"
    },
    {
        "idx": 13,
        "fname": "repouso_13_ready_stance_joelhos_cima",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE (JOELHOS PARA CIMA)",
        "dist": "2.0m (Joelhos para cima)",
        "postura": "Mais perto da câmera, postura firme de atenção",
        "acao": "Mãos juntas segurando o cabo à frente, tronco estável"
    },
    {
        "idx": 14,
        "fname": "repouso_14_ready_stance_weight_shift",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE COM GINGA DE PERNAS",
        "dist": "2.5m a 3.5m",
        "postura": "Posição de prontidão com peso ativo",
        "acao": "Pequena oscilação sutil de pernas (weight shift) sem mover braços"
    },
    {
        "idx": 15,
        "fname": "repouso_15_troca_empunhadura_sutil",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "TROCA SUTIL DE EMPUNHADURA",
        "dist": "2.5m (Média Distância)",
        "postura": "Ready stance clássico segurando o cabo",
        "acao": "Gire levemente o cabo da raquete entre as mãos (ajuste de grip)"
    },
    {
        "idx": 16,
        "fname": "repouso_16_ready_stance_alto",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE DE POSTURA ALTA",
        "dist": "2.5m a 3.5m",
        "postura": "Postura mais ereta, joelhos pouco destravados",
        "acao": "Raquete mais alta no peito (espera de segundo saque do oponente)"
    },
    {
        "idx": 17,
        "fname": "repouso_17_ready_stance_baixo_aberto",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE OPEN STANCE BAIXO",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Pernas bem afastadas, joelhos bem baixos (base aberta)",
        "acao": "Centro de gravidade baixo (postura de devolução agressiva)"
    },
    {
        "idx": 18,
        "fname": "repouso_18_ready_stance_inclinado_dir",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE INCLINADO À DIREITA",
        "dist": "2.5m a 3.5m",
        "postura": "Tronco e olhar virados 30° para a direita da quadra",
        "acao": "Acompanhando rally imaginário no lado direito sem golpear"
    },
    {
        "idx": 19,
        "fname": "repouso_19_ready_stance_inclinado_esq",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE INCLINADO À ESQUERDA",
        "dist": "2.5m a 3.5m",
        "postura": "Tronco e olhar virados 30° para a esquerda da quadra",
        "acao": "Acompanhando rally imaginário no lado esquerdo sem golpear"
    },
    {
        "idx": 20,
        "fname": "repouso_20_ready_stance_ajuste_pes",
        "lote": "LOTE B: READY STANCE (PRONTIDÃO DO TÊNIS)",
        "title": "READY STANCE COM AJUSTE DE PÉS",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Base de prontidão com pés ativos",
        "acao": "Pequenos toques e ajustes de sola de tênis no chão no lugar"
    },

    # LOTE C: Footwork, Split-Step & Transições (21 a 30)
    {
        "idx": 21,
        "fname": "repouso_21_split_step_simulado",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "SPLIT-STEP SIMULADO NO LUGAR",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Em pé no centro da sua área",
        "acao": "Dê pequenos split-steps (pulinho e aterrissagem em prontidão)"
    },
    {
        "idx": 22,
        "fname": "repouso_22_passos_laterais_esquerda",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "PASSOS LATERAIS PARA A ESQUERDA",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Postura atlética no centro",
        "acao": "Dê 2 passos laterais para a esquerda e volte devagar ao centro"
    },
    {
        "idx": 23,
        "fname": "repouso_23_passos_laterais_direita",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "PASSOS LATERAIS PARA A DIREITA",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Postura atlética no centro",
        "acao": "Dê 2 passos laterais para a direita e volte devagar ao centro"
    },
    {
        "idx": 24,
        "fname": "repouso_24_passo_frente_retorno",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "PASSO À FRENTE E RETORNO À BASE",
        "dist": "2.5m a 3.5m",
        "postura": "Comece no fundo",
        "acao": "Dê 1 passo largo à frente em prontidão e retorne 1 passo para trás"
    },
    {
        "idx": 25,
        "fname": "repouso_25_recuo_fundo_quadra",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "RECUO PARA O FUNDO E RETORNO",
        "dist": "2.5m a 3.5m",
        "postura": "Comece na média distância (2.5m)",
        "acao": "Dê 2 passos para trás e retorne suavemente à marca central"
    },
    {
        "idx": 26,
        "fname": "repouso_26_rotacao_tronco_sem_golpe",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "ROTAÇÃO DE TRONCO SEM GOLPE",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé no centro",
        "acao": "Gire ombros acompanhando bola imaginária passando alto por cima"
    },
    {
        "idx": 27,
        "fname": "repouso_27_caminhada_esquerda_direita",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "CAMINHADA DA ESQUERDA PARA DIREITA",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Fundo de quadra no lado esquerdo",
        "acao": "Caminhe calmamente cruzando até o lado direito da tela"
    },
    {
        "idx": 28,
        "fname": "repouso_28_caminhada_direita_esquerda",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "CAMINHADA DA DIREITA PARA ESQUERDA",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Fundo de quadra no lado direito",
        "acao": "Caminhe calmamente cruzando de volta até o lado esquerdo da tela"
    },
    {
        "idx": 29,
        "fname": "repouso_29_trote_leve_soltura",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "TROTE LEVE NO LUGAR (SOLTURA)",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "No centro da quadra",
        "acao": "Faça um trote bem leve e ritmado no lugar para soltar as pernas"
    },
    {
        "idx": 30,
        "fname": "repouso_30_transicao_defesa_centro",
        "lote": "LOTE C: FOOTWORK, SPLIT-STEP & TRANSIÇÕES",
        "title": "RECUPERAÇÃO AO CENTRO DE QUADRA",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Comece em um dos cantos da câmera",
        "acao": "Desloque-se até o centro e freie firme amortecendo em prontidão"
    },

    # LOTE D: Gestos Casuais & Movimentos Cotidianos (31 a 40)
    {
        "idx": 31,
        "fname": "repouso_31_limpar_suor_testa",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "LIMPAR SUOR DA TESTA",
        "dist": "2.0m a 2.5m",
        "postura": "Em pé casual",
        "acao": "Passe o antebraço ou punho na testa suavemente para limpar o suor"
    },
    {
        "idx": 32,
        "fname": "repouso_32_ajeitar_oculos_cabelo",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "AJEITAR ÓCULOS OU CABELO",
        "dist": "2.0m a 2.5m",
        "postura": "Em pé casual",
        "acao": "Leve a mão ao rosto/óculos/cabelo em gesto natural do dia a dia"
    },
    {
        "idx": 33,
        "fname": "repouso_33_beber_agua_gesto",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "GESTO DE BEBER ÁGUA",
        "dist": "2.0m a 2.5m",
        "postura": "Em pé relaxado",
        "acao": "Simule levar garrafa d'água à boca, beber um gole e abaixar o braço"
    },
    {
        "idx": 34,
        "fname": "repouso_34_alongamento_suave_ombro",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "ALONGAMENTO SUAVE DE OMBRO",
        "dist": "2.5m",
        "postura": "Em pé ereto",
        "acao": "Puxe suavemente um dos braços na frente do peito (alongar deltoide)"
    },
    {
        "idx": 35,
        "fname": "repouso_35_ajeitar_cordas_raquete",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "AJEITAR AS CORDAS DA RAQUETE",
        "dist": "2.0m a 2.5m",
        "postura": "Olhando para as mãos à frente",
        "acao": "Passe os dedos simulando alinhar a trama das cordas da raquete"
    },
    {
        "idx": 36,
        "fname": "repouso_36_comemoracao_comedida",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "COMEMORAÇÃO COMEDIDA DE PONTO",
        "dist": "2.0m a 2.5m",
        "postura": "Em pé de frente",
        "acao": "Cerre o punho junto ao peito em gesto de 'Vamos!' sem braçada ampla"
    },
    {
        "idx": 37,
        "fname": "repouso_37_olhar_lado_apontar",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "APONTAR PARA FORA DA QUADRA",
        "dist": "2.5m",
        "postura": "Em pé de frente",
        "acao": "Aponte o dedo indicador para o lado indicando bola fora/marcação"
    },
    {
        "idx": 38,
        "fname": "repouso_38_maos_na_cintura",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "MÃOS NA CINTURA (DESCANSO)",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé ereto",
        "acao": "Apoie ambas as mãos nos quadris, respirando e descansando"
    },
    {
        "idx": 39,
        "fname": "repouso_39_bracos_cruzados_peito",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "BRAÇOS CRUZADOS NO PEITO",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé de frente",
        "acao": "Cruze os braços sobre o peito e fique observando a quadra"
    },
    {
        "idx": 40,
        "fname": "repouso_40_sacudir_pulsos_relax",
        "lote": "LOTE D: GESTOS CASUAIS & COTIDIANOS",
        "title": "SACUDIR PULSOS E BRAÇOS",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé relaxado",
        "acao": "Sacuda suavemente as mãos e pulsos para baixo para soltar a tensão"
    },

    # LOTE E: Variações de Luz, Sombra e Profundidade (41 a 50)
    {
        "idx": 41,
        "fname": "repouso_41_caminhada_fundo_para_frente",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "APROXIMAÇÃO: FUNDO PARA FRENTE",
        "dist": "3.5m -> 1.5m",
        "postura": "Comece no fundo (3.5m)",
        "acao": "Caminhe calmamente até chegar perto da câmera (1.5m)"
    },
    {
        "idx": 42,
        "fname": "repouso_42_caminhada_frente_para_fundo",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "RECUO: FRENTE PARA O FUNDO",
        "dist": "1.5m -> 3.5m",
        "postura": "Comece perto da câmera (1.5m)",
        "acao": "Caminhe de costas ou de frente voltando até o fundo (3.5m)"
    },
    {
        "idx": 43,
        "fname": "repouso_43_diagonal_fundo_esq_frente_dir",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "DIAGONAL: FUNDO-ESQ PARA FRENTE-DIR",
        "dist": "3.5m -> 2.0m",
        "postura": "Comece no fundo à esquerda",
        "acao": "Desloque-se em diagonal suavemente até a frente direita"
    },
    {
        "idx": 44,
        "fname": "repouso_44_diagonal_fundo_dir_frente_esq",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "DIAGONAL: FUNDO-DIR PARA FRENTE-ESQ",
        "dist": "3.5m -> 2.0m",
        "postura": "Comece no fundo à direita",
        "acao": "Desloque-se em diagonal suavemente até a frente esquerda"
    },
    {
        "idx": 45,
        "fname": "repouso_45_luz_lateral_sombra",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "CORPO INTEIRO COM LUZ/SOMBRA LATERAL",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Em pé relaxado a 3.5m",
        "acao": "Posição estática com iluminação de janela/sombra parcial do quarto"
    },
    {
        "idx": 46,
        "fname": "repouso_46_abaixar_pegar_bola",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "ABAIXAR PARA PEGAR BOLA NO CHÃO",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Em pé no centro",
        "acao": "Agache com calma, toque o chão simulando pegar bola e levante"
    },
    {
        "idx": 47,
        "fname": "repouso_47_sentar_levantar_cadeira",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "SENTAR E LEVANTAR DA CADEIRA",
        "dist": "3.5m (Fundo do Quarto)",
        "postura": "Próximo à sua cadeira ao fundo",
        "acao": "Sente-se na cadeira, respire 3 segundos e levante com naturalidade"
    },
    {
        "idx": 48,
        "fname": "repouso_48_ginga_espera_fundo",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "GINGA DE ESPERA NO FUNDO DE QUADRA",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Fundo de quadra em prontidão",
        "acao": "Balanço leve e rítmico de pernas no fundo da quadra"
    },
    {
        "idx": 49,
        "fname": "repouso_49_caminhada_pos_ponto",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "CAMINHADA DE RETORNO PÓS-PONTO",
        "dist": "3.5m (Corpo Inteiro)",
        "postura": "Vindo do fundo da quadra",
        "acao": "Caminhe de volta à marca central com a raquete baixa e olhar ereto"
    },
    {
        "idx": 50,
        "fname": "repouso_50_descanso_final",
        "lote": "LOTE E: PROFUNDIDADE, LUZ & TRANSIÇÕES FINAIS",
        "title": "DESCANSO FINAL DO TREINAMENTO",
        "dist": "2.5m a 3.5m",
        "postura": "Em pé totalmente relaxado",
        "acao": "Postura de descanso e fechamento do treino de repouso"
    }
]

def play_beep_async(freq, duration_ms):
    """Executa um sinal sonoro em segundo plano sem travar o vídeo."""
    if HAS_SOUND:
        try:
            t = threading.Thread(target=lambda: winsound.Beep(freq, duration_ms), daemon=True)
            t.start()
            return t
        except Exception:
            pass
    return None

def draw_mediapipe_skeleton(display, landmarks, width, height):
    """Renderiza os ossos anatômicos e articulações MediaPipe sobre o frame."""
    if not landmarks or len(landmarks) < 25:
        return

    # Linhas dos segmentos ósseos
    for i, j in POSE_CONNECTIONS:
        if i < len(landmarks) and j < len(landmarks):
            lm_i = landmarks[i]
            lm_j = landmarks[j]
            vis_i = getattr(lm_i, 'visibility', 1.0)
            vis_j = getattr(lm_j, 'visibility', 1.0)
            if vis_i > 0.35 and vis_j > 0.35:
                x1, y1 = int(lm_i.x * width), int(lm_i.y * height)
                x2, y2 = int(lm_j.x * width), int(lm_j.y * height)
                cv2.line(display, (x1, y1), (x2, y2), (0, 230, 140), 2, cv2.LINE_AA)

    # Articulações corporais
    for idx, lm in enumerate(landmarks):
        vis = getattr(lm, 'visibility', 1.0)
        if vis > 0.35:
            cx, cy = int(lm.x * width), int(lm.y * height)
            if idx in [15, 16, 17, 18, 19, 20, 21, 22]:  # Mãos e Pulsos
                cv2.circle(display, (cx, cy), 4, (255, 190, 0), -1, cv2.LINE_AA)
            elif idx in [11, 12, 13, 14, 23, 24, 25, 26, 27, 28]:  # Articulações Principais
                cv2.circle(display, (cx, cy), 5, (0, 215, 255), -1, cv2.LINE_AA)
                cv2.circle(display, (cx, cy), 6, (255, 255, 255), 1, cv2.LINE_AA)
            elif idx in [0, 2, 5, 7, 8]:  # Cabeça
                cv2.circle(display, (cx, cy), 3, (0, 240, 255), -1, cv2.LINE_AA)

def run_autonomous_session(cap, landmarker, start_video=2, end_video=50, briefing_sec=8, countdown_sec=5, duration_sec=12.0):
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    fps = 30.0

    print("=" * 75)
    print(" TENNISSYNC: MÓDULO AUTÔNOMO DE GRAVAÇÃO (50 VÍDEOS DE REPOUSO)")
    print(" - Totalmente guiado na tela do OpenCV com instruções passo a passo")
    print(" - Rastreamento MediaPipe Pose 3D ao vivo na tela")
    print(" - Transição automática entre vídeos com aviso sonoro")
    print(" - Controles rápidos: [ESPAÇO]: Iniciar Já | [P]: Pausar | [R]: Regravar | [S]: Pular | [Q]: Sair")
    print("=" * 75)

    catalog_map = {item["idx"]: item for item in CATALOG}
    current_idx = start_video

    while current_idx <= end_video:
        item = catalog_map.get(current_idx)
        if not item:
            break

        idx = item["idx"]
        fname = item["fname"]
        title = item["title"]
        lote_name = item["lote"]
        dist = item["dist"]
        postura = item["postura"]
        acao = item["acao"]
        out_path = os.path.join(DEST_DIR, f"{fname}.mp4")

        print(f"\n>>> [VÍDEO {idx:02d}/50]: {title}")
        print(f"    Enquadramento: {dist}")
        print(f"    Postura: {postura}")
        print(f"    Ação: {acao}")

        # Som suave de transição avisando que a tela mudou para o próximo vídeo
        play_beep_async(600, 120)

        # ====================================================================
        # FASE 1: BRIEFING & INSTRUÇÕES NA TELA (com auto-avanço de briefing_sec)
        # ====================================================================
        b_start = time.time()
        is_paused = False
        skip_to_countdown = False

        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            if not is_paused:
                b_elapsed = time.time() - b_start
                b_rem = max(0, briefing_sec - int(b_elapsed))
            else:
                b_rem = 0

            # MediaPipe ao vivo
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_img)

            display = frame.copy()
            has_pose = False
            if res.pose_landmarks:
                has_pose = True
                draw_mediapipe_skeleton(display, res.pose_landmarks[0], width, height)

            # 1. Header Superior Translúcido
            cv2.rectangle(display, (0, 0), (width, 50), (15, 18, 24), -1)
            cv2.putText(display, f"[{idx:02d}/50] {title}", (14, 25), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 230, 140), 2)
            cv2.putText(display, lote_name, (14, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

            # Badge do MediaPipe
            if has_pose:
                cv2.circle(display, (width - 165, 24), 5, (0, 230, 140), -1)
                cv2.putText(display, "MediaPipe 3D Ativo", (width - 152, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 230, 140), 1)
            else:
                cv2.circle(display, (width - 165, 24), 5, (0, 140, 255), -1)
                cv2.putText(display, "Procurando Atleta...", (width - 152, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 140, 255), 1)

            # 2. Card de Instruções Inferior Translúcido
            card_h = 145
            card_y = height - card_h - 10
            cv2.rectangle(display, (10, card_y), (width - 10, height - 10), (12, 14, 18), -1)
            cv2.rectangle(display, (10, card_y), (width - 10, height - 10), (0, 230, 140), 1)

            cv2.putText(display, "INSTRUÇÕES DA POSTURA:", (20, card_y + 22), cv2.FONT_HERSHEY_DUPLEX, 0.48, (0, 230, 140), 1)
            cv2.putText(display, f"1. ENQUADRAMENTO: {dist}", (20, card_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 215, 255), 1)
            cv2.putText(display, f"2. POSTURA: {postura}", (20, card_y + 68), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1)
            cv2.putText(display, f"3. EXECUÇÃO: {acao}", (20, card_y + 91), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 230, 200), 1)

            # Linha inferior do card com status de tempo / controles
            cv2.rectangle(display, (10, height - 32), (width - 10, height - 10), (20, 24, 30), -1)
            if is_paused:
                cv2.putText(display, "[PAUSADO] Pressione [ESPAÇO] para iniciar a gravação deste vídeo", (20, height - 17), cv2.FONT_HERSHEY_DUPLEX, 0.42, (0, 215, 255), 1)
            else:
                cv2.putText(display, f"INICIANDO EM: {b_rem}s  |  [ESPAÇO]: Ir Agora  |  [P]: Pausar  |  [R]: Voltar  |  [Q]: Sair", 
                            (20, height - 17), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (170, 170, 170), 1)

            cv2.imshow("TenniSync - Gravador Autônomo com MediaPipe Pose 3D", display)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n[ENCERRADO PELO USUÁRIO]")
                return
            elif key == ord('p'):
                is_paused = not is_paused
            elif key == 32 or key == 13: # Barra de Espaço ou Enter
                skip_to_countdown = True
                break
            elif key == ord('s'): # Pular este vídeo
                print(f"[PULADO] Vídeo {idx:02d} pulado.")
                current_idx += 1
                break
            elif key == ord('r'): # Voltar para o vídeo anterior
                current_idx = max(1, current_idx - 1)
                break

            if not is_paused and b_elapsed >= briefing_sec:
                break

        if key in [ord('s'), ord('r')]:
            continue

        # ====================================================================
        # FASE 2: CONTAGEM DE 5 SEGUNDOS COM BEEP CONTÍNUO
        # ====================================================================
        print(f" -> Contagem de {countdown_sec}s com BEEP CONTÍNUO...")
        play_beep_async(900, int(countdown_sec * 1000))

        c_start = time.time()
        cancelled = False

        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            c_elapsed = time.time() - c_start
            c_rem = countdown_sec - int(c_elapsed)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_img)

            display = frame.copy()
            if res.pose_landmarks:
                draw_mediapipe_skeleton(display, res.pose_landmarks[0], width, height)

            # Header
            cv2.rectangle(display, (0, 0), (width, 50), (15, 18, 24), -1)
            cv2.putText(display, f"[{idx:02d}/50] {title}", (14, 25), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 230, 140), 2)
            cv2.putText(display, f"ENQUADRAMENTO: {dist}", (14, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 215, 255), 1)

            # Centro da tela: Banner de Contagem
            cv2.rectangle(display, (width // 2 - 210, height // 2 - 45), (width // 2 + 210, height // 2 + 35), (10, 12, 16), -1)
            cv2.rectangle(display, (width // 2 - 210, height // 2 - 45), (width // 2 + 210, height // 2 + 35), (0, 215, 255), 2)
            if c_rem > 0:
                cv2.putText(display, f"POSICIONE-SE: {c_rem}s", (width // 2 - 170, height // 2), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 215, 255), 2)
                cv2.putText(display, "Ouvindo Beep continuo...", (width // 2 - 130, height // 2 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 230, 140), 1)
            else:
                cv2.putText(display, "GRAVANDO AGORA!", (width // 2 - 170, height // 2 + 5), cv2.FONT_HERSHEY_DUPLEX, 1.15, (0, 0, 255), 2)

            cv2.imshow("TenniSync - Gravador Autônomo com MediaPipe Pose 3D", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[ENCERRADO PELO USUÁRIO]")
                return

            if c_elapsed >= countdown_sec:
                break

        # ====================================================================
        # FASE 3: GRAVAÇÃO ATIVA DOS FRAMES LIMPOS (12 SEGUNDOS)
        # ====================================================================
        print(f" -> [BEEP PAROU: GRAVANDO {fname}.mp4 POR {duration_sec}s... MANTENHA A POSTURA!]")
        recorded_frames = []
        r_start = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                continue
            r_elapsed = time.time() - r_start
            rem_rec = duration_sec - r_elapsed

            # O frame limpo vai para o dataset
            recorded_frames.append(frame.copy())

            # MediaPipe ao vivo na tela
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = landmarker.detect(mp_img)

            display = frame.copy()
            if res.pose_landmarks:
                draw_mediapipe_skeleton(display, res.pose_landmarks[0], width, height)

            # Barra superior de gravação com indicador vermelho pulsante
            cv2.rectangle(display, (0, 0), (width, 55), (15, 18, 24), -1)
            cv2.circle(display, (25, 27), 7, (0, 0, 255), -1)
            cv2.putText(display, f"GRAVANDO [{idx:02d}/50]: {title}", (42, 26), cv2.FONT_HERSHEY_DUPLEX, 0.60, (0, 0, 255), 2)
            cv2.putText(display, f"MANTENHA A POSTURA  |  TEMPO RESTANTE: {max(0.0, rem_rec):.1f}s", (42, 47), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 215, 255), 1)

            # Barra de progresso verde inferior
            prog_w = int((r_elapsed / duration_sec) * width)
            cv2.rectangle(display, (0, height - 10), (prog_w, height), (0, 230, 140), -1)

            cv2.imshow("TenniSync - Gravador Autônomo com MediaPipe Pose 3D", display)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n[ENCERRADO PELO USUÁRIO]")
                return

            if r_elapsed >= duration_sec:
                break

        # Sinal sonoro duplo de sucesso
        play_beep_async(1200, 150)
        time.sleep(0.16)
        play_beep_async(1600, 250)

        # Salvar o vídeo puro em MP4
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        for f in recorded_frames:
            writer.write(f)
        writer.release()

        size_kb = os.path.getsize(out_path) // 1024 if os.path.exists(out_path) else 0
        total_in_dir = len([f for f in os.listdir(DEST_DIR) if f.endswith(".mp4")])
        print(f"[CONCLUÍDO] Salvo: {fname}.mp4 ({len(recorded_frames)} frames, {size_kb} KB) | Progresso: {total_in_dir}/50")

        # Tela de Confirmação Rápida (1.5 segundos) antes de passar para o próximo
        f_start = time.time()
        while time.time() - f_start < 1.5:
            disp_finish = np.zeros((height, width, 3), dtype=np.uint8)
            cv2.putText(disp_finish, f"VÍDEO {idx:02d} GRAVADO COM SUCESSO!", (width // 2 - 210, height // 2 - 20), cv2.FONT_HERSHEY_DUPLEX, 0.75, (0, 230, 140), 2)
            cv2.putText(disp_finish, f"Total no Dataset: {total_in_dir} de 50 videos", (width // 2 - 160, height // 2 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (210, 210, 210), 1)
            cv2.putText(disp_finish, "Carregando proxima instrucao...", (width // 2 - 140, height // 2 + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 215, 255), 1)
            cv2.imshow("TenniSync - Gravador Autônomo com MediaPipe Pose 3D", disp_finish)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                return

        # Próximo vídeo!
        current_idx += 1

    # Tela Final de Encerramento (50 Vídeos Gravados!)
    disp_final = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(disp_final, "PARABENS! DATASET COMPLETO!", (width // 2 - 220, height // 2 - 20), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 230, 140), 2)
    cv2.putText(disp_final, "50 videos de repouso gravados com sucesso.", (width // 2 - 200, height // 2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.imshow("TenniSync - Gravador Autônomo com MediaPipe Pose 3D", disp_final)
    cv2.waitKey(3000)

def main():
    parser = argparse.ArgumentParser(description="Gravador Autônomo dos 50 Vídeos de Repouso.")
    parser.add_argument("--start", type=int, default=None, help="Número do vídeo inicial (padrão: próximo não gravado)")
    parser.add_argument("--end", type=int, default=50, help="Número do vídeo final (1 a 50)")
    parser.add_argument("--camera", type=int, default=0, help="Índice da câmera (padrão: 0)")
    parser.add_argument("--briefing", type=int, default=8, help="Tempo em segundos do card de instruções na tela (padrão: 8s)")
    parser.add_argument("--countdown", type=int, default=5, help="Contagem com beep contínuo em segundos (padrão: 5s)")
    parser.add_argument("--duration", type=float, default=12.0, help="Duração de gravação de cada vídeo em segundos (padrão: 12s)")
    args = parser.parse_args()

    # Detectar automaticamente próximo vídeo não gravado se não especificado
    if args.start is None:
        existing_files = set(os.listdir(DEST_DIR))
        next_unrecorded = 1
        for item in CATALOG:
            if f"{item['fname']}.mp4" not in existing_files:
                next_unrecorded = item["idx"]
                break
            next_unrecorded = 51
        args.start = min(50, next_unrecorded)
        print(f"[Auto-Resume] Iniciando automaticamente a partir do Vídeo {args.start:02d}...")

    # Carregar modelo MediaPipe Pose
    model_path = os.path.join(BASE_DIR, "pose_landmarker_full.task")
    if not os.path.exists(model_path):
        model_path = os.path.join(BASE_DIR, "pose_landmarker_lite.task")
    print(f"[MediaPipe] Carregando modelo: {os.path.basename(model_path)}...")
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(base_options=base_options, running_mode=vision.RunningMode.IMAGE)
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"[ERRO] Falha ao abrir câmera {args.camera}.")
        sys.exit(1)

    try:
        run_autonomous_session(cap, landmarker, start_video=args.start, end_video=args.end, 
                               briefing_sec=args.briefing, countdown_sec=args.countdown, duration_sec=args.duration)
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
