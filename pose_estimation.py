import cv2
import mediapipe as mp
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles
import numpy as np
import collections
import serial

MAPA_LEDS = {
    "ombro_esq": b'A', "ombro_dir": b'B', "cotovelo_esq": b'C', 
    "cotovelo_dir": b'D', "pulso_esq": b'E', "pulso_dir": b'F',
    "quadril_esq": b'G', "quadril_dir": b'H', "joelho_esq": b'I', 
    "joelho_dir": b'J', "tornozelo_esq": b'K', "tornozelo_dir": b'L'
}

# Tenta importar torch, mas lida com o caso de não estar instalado
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("Aviso: PyTorch não está instalado. O modelo mock receberá numpy arrays.")

# Importações dos nossos módulos
from angle_calculator import get_landmark_coord
import rule_engine
from models.tennis_transformer import TennisTransformerGPU

def process_landmarks_to_tensor(landmarks):
    """
    Recebe os 33 landmarks e os centraliza com base no quadril.
    Retorna um array (33, 3).
    """
    coords = np.array([get_landmark_coord(lm) for lm in landmarks], dtype=np.float32)
    
    # Quadril: landmarks 23 e 24
    hip_left = coords[23]
    hip_right = coords[24]
    
    # Ponto central do quadril
    hip_center = (hip_left + hip_right) / 2.0
    
    # Centralização
    centered_coords = coords - hip_center
    return centered_coords

def main():
    # Inicializa o modelo de classificação de tênis
    tennis_model = TennisTransformerGPU()
    if HAS_TORCH:
        tennis_model = tennis_model.to('cuda')
    
    # Caminho para o modelo MediaPipe
    model_path = 'pose_landmarker_lite.task'
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE)
    landmarker = vision.PoseLandmarker.create_from_options(options)

    # Inicia a captura de vídeo
    cap = cv2.VideoCapture(1)

    pTime = 0
    
    # Buffer de frames deslizante (60 frames max)
    frame_buffer = collections.deque(maxlen=60)
    
    # Variáveis de feedback
    current_feedback = ""
    feedback_time = 0

    # Inicialização da porta Serial do Arduino (Painel IoT)
    try:
        feedback_arduino = serial.Serial('COM4', 9600, timeout=0)
    except Exception as e:
        feedback_arduino = None
        print(f"Aviso: Painel de LEDs desconectado na porta COM4. Erro: {e}")
        
    led_active = False

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            time.sleep(0.1)
            continue

        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

        # Inferência do MediaPipe
        detection_result = landmarker.detect(mp_image)

        annotated_image = np.copy(frame)
        
        if detection_result.pose_landmarks:
            pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
            
            # Trabalha com o primeiro pose detectado (assumindo 1 jogador)
            landmarks = detection_result.pose_landmarks[0]
            
            # Desenhar no frame
            drawing_utils.draw_landmarks(
                image=annotated_image,
                landmark_list=landmarks,
                connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
                landmark_drawing_spec=pose_landmark_style
            )
            
            # Extrair, centralizar e adicionar ao buffer
            centered_coords = process_landmarks_to_tensor(landmarks)
            frame_buffer.append(centered_coords)
            
            # Realizar inferência com o modelo TennisTransformerGPU se o buffer estiver cheio
            if len(frame_buffer) == 60:
                # Shape: (60, 33, 3) -> (1, 60, 33, 3)
                input_data = np.stack(frame_buffer)
                input_data = np.expand_dims(input_data, axis=0)
                
                if HAS_TORCH:
                    input_tensor = torch.tensor(input_data, dtype=torch.float32).to('cuda')
                else:
                    input_tensor = input_data
                    
                # Inferência
                class_id, confidence = tennis_model(input_tensor)
                
                # Regra: se for golpe (0 a 2) com alta confiança (> 0.85)
                if class_id in [0, 1, 2] and confidence > 0.85:
                    stroke_names = {0: "Forehand", 1: "Backhand", 2: "Saque"}
                    stroke_name = stroke_names[class_id]
                    
                    # Motor de Regras: Avaliar biomecânica neste momento específico
                    feedback_str, angles_dict, failed_joints = rule_engine.evaluate_stroke(class_id, landmarks)
                    
                    # Controle IoT
                    if feedback_arduino is not None:
                        if failed_joints:
                            for joint in failed_joints:
                                feedback_arduino.write(MAPA_LEDS[joint])
                            led_active = True
                        elif led_active:
                            feedback_arduino.write(b'R')
                            led_active = False

                    # Atualizar feedback para mostrar na tela
                    current_feedback = f"{stroke_name} ({confidence:.2f}): {feedback_str}"
                    feedback_time = time.time()
                    
                    # Limpa o buffer parcialmente para não ficar disparando sequencialmente
                    # (Cooldown de 20 frames)
                    for _ in range(20):
                        frame_buffer.popleft()

        # Mostra o feedback por 2 segundos
        if time.time() - feedback_time < 2.0:
            cv2.putText(annotated_image, current_feedback, (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            current_feedback = ""

        cv2.putText(annotated_image, f'FPS: {int(fps)}', (20, 70), cv2.FONT_HERSHEY_PLAIN, 3, (0, 255, 0), 3)
        cv2.imshow('MediaPipe + Tennis GPU - Q para sair', annotated_image)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()

if __name__ == '__main__':
    main()
