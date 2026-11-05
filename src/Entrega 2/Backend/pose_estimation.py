import time
import os
import sys
import collections

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.vision import drawing_utils
    from mediapipe.tasks.python.vision import drawing_styles
    HAS_MEDIAPIPE = True
except ImportError:
    mp = None
    HAS_MEDIAPIPE = False

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    serial = None
    HAS_SERIAL = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from angle_calculator import get_landmark_coord
import rule_engine
from models.tennis_transformer import TennisTransformerGPU
from gamification_engine import GamificationEngine
from hud_renderer import TennisHUD

MAPA_LEDS = {
    "ombro_esq": b'A', "ombro_dir": b'B', "cotovelo_esq": b'C', 
    "cotovelo_dir": b'D', "pulso_esq": b'E', "pulso_dir": b'F',
    "quadril_esq": b'G', "quadril_dir": b'H', "joelho_esq": b'I', 
    "joelho_dir": b'J', "tornozelo_esq": b'K', "tornozelo_dir": b'L'
}

def process_landmarks_to_tensor(landmarks):
    """
    Recebe os 33 landmarks e os centraliza com base no quadril.
    Retorna um array (33, 3).
    """
    if not HAS_NUMPY:
        return None
    coords = np.array([get_landmark_coord(lm) for lm in landmarks], dtype=np.float32)
    hip_left = coords[23]
    hip_right = coords[24]
    hip_center = (hip_left + hip_right) / 2.0
    centered_coords = coords - hip_center
    return centered_coords

def is_valid_human_pose(landmarks) -> bool:
    """
    Verifica se a pose detectada possui pontos anatômicos corporais reais.
    Exige que pelo menos o tronco superior (ombros ou nariz) esteja presente.
    """
    if not landmarks or len(landmarks) < 25:
        return False
    
    # 0: nariz, 11: ombro esq, 12: ombro dir, 23: quadril esq, 24: quadril dir
    key_indices = [0, 11, 12, 23, 24]
    valid_count = 0
    for idx in key_indices:
        lm = landmarks[idx]
        vis = getattr(lm, 'visibility', None)
        presence = getattr(lm, 'presence', None)
        
        # Considera válido se presença for razoável ou coordenada y dentro da imagem
        has_confidence = (vis is None or vis >= 0.3) and (presence is None or presence >= 0.3)
        in_bounds = 0.0 <= lm.y <= 1.0 and 0.0 <= lm.x <= 1.0
        if has_confidence and in_bounds:
            valid_count += 1

    return valid_count >= 2


class TennisSyncEngine:
    """
    Motor desacoplado de Processamento Biomecânico, Visão Computacional e Replay.
    Contém:
    - Buffer circular de 5 segundos em memória com esqueletos MediaPipe desenhados.
    - Persistência visual do feedback por 3.5 segundos sem piscar.
    - Cooldown anti-falsos positivos de 2.5 segundos.
    - Exportador automático do clipe de replay .mp4 para o frontend.
    """
    def __init__(self, source="0", lateralidade="destro", arduino_port="COM4"):
        self.source = int(source) if str(source).isdigit() else source
        self.lateralidade = lateralidade
        self.device = 'cuda' if (HAS_TORCH and torch.cuda.is_available()) else 'cpu'

        # Inicializa o modelo Transformer treinado
        self.tennis_model = TennisTransformerGPU()
        if HAS_TORCH:
            self.tennis_model = self.tennis_model.to(self.device)

        # Inicializa o detector MediaPipe
        self.landmarker = None
        if HAS_MEDIAPIPE:
            model_path = os.path.join(BASE_DIR, 'pose_landmarker_lite.task')
            if os.path.exists(model_path):
                try:
                    base_options = python.BaseOptions(model_asset_path=model_path)
                    options = vision.PoseLandmarkerOptions(
                        base_options=base_options,
                        running_mode=vision.RunningMode.IMAGE,
                        min_pose_detection_confidence=0.45,
                        min_pose_presence_confidence=0.45,
                        min_tracking_confidence=0.45
                    )
                    self.landmarker = vision.PoseLandmarker.create_from_options(options)
                except Exception as e:
                    print(f"[TenniSync Backend] Erro ao carregar MediaPipe: {e}")

        # Buffer temporal de 60 frames para a rede Transformer
        self.frame_buffer = collections.deque(maxlen=60)

        # Buffer circular de Replay: 5 segundos de frames a 30 FPS = 150 frames em memória
        self.replay_buffer = collections.deque(maxlen=150)
        self.replays_dir = os.path.join(BASE_DIR, "replays")
        os.makedirs(self.replays_dir, exist_ok=True)
        self.latest_replay_filename = None
        self.latest_replay_url = None

        # Arduino Serial para hardware IoT
        self.feedback_arduino = None
        if HAS_SERIAL:
            try:
                self.feedback_arduino = serial.Serial(arduino_port, 9600, timeout=0)
            except Exception as e:
                self.feedback_arduino = None

        self.led_active = False
        self.p_time = time.time()
        self.fps = 30.0

        # Estados de telemetria
        self.current_stroke_id = 3
        self.current_stroke_name = "Repouso"
        self.current_confidence = 0.0
        self.current_feedback = "Posicione-se em frente à câmera"
        self.failed_joints = []
        self.angles = {"elbow_r": 120, "elbow_l": 120, "knee_r": 160, "knee_l": 160}
        self.latest_frame = None
        self.current_landmarks = None

        # Controle de tempo e persistência na tela
        self.stroke_display_until = 0.0      # Mantém feedback visível por 3.5s
        self.stroke_cooldown_until = 0.0     # Impede disparos repetidos por 2.5s
        self.event_id = 0                    # Identificador único de cada golpe real
        self.athlete_detected = False
        self.is_dark = False
        self.no_pose_consecutive = 0

        # Motor de Gamificação e Renderizador HUD
        self.game_engine = GamificationEngine()
        self.hud = TennisHUD()

    def set_lateralidade(self, lateralidade):
        self.lateralidade = lateralidade

    def reset_rally(self):
        self.game_engine.reset_rally()

    def reset_session(self):
        self.game_engine.reset_session()

    def _save_replay_clip(self, stroke_name: str, event_id: int):
        """
        Salva os frames dos últimos 5 segundos do buffer de replay
        em um arquivo de vídeo .mp4 na pasta replays.
        """
        if not HAS_CV2 or len(self.replay_buffer) < 15:
            return

        frames_snapshot = list(self.replay_buffer)
        h, w = frames_snapshot[0].shape[:2]
        fps_out = max(15.0, min(30.0, self.fps))

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        unique_name = f"replay_{timestamp_str}_{stroke_name.lower()}_e{event_id}.mp4"
        unique_path = os.path.join(self.replays_dir, unique_name)
        latest_path = os.path.join(self.replays_dir, "replay_latest.mp4")

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        try:
            out = cv2.VideoWriter(unique_path, fourcc, fps_out, (w, h))
            for f in frames_snapshot:
                out.write(f)
            out.release()

            if os.path.exists(unique_path):
                import shutil
                shutil.copyfile(unique_path, latest_path)

            self.latest_replay_filename = unique_name
            self.latest_replay_url = f"/api/replay/latest?t={int(time.time()*1000)}"
            print(f"[TenniSync Replay] Gravado clipe de 5s ({len(frames_snapshot)} frames): {unique_name}", flush=True)
        except Exception as e:
            print(f"[TenniSync Replay] Erro ao salvar vídeo de replay: {e}", flush=True)

    def process_frame(self, frame, render_hud=True):
        """
        Processa um frame de vídeo, atualiza inferência da IA, diagnóstico biomecânico e gamificação.
        Se render_hud=True, desenha a HUD de jogo sobre o frame.
        Retorna dicionário com a telemetria serializável em JSON.
        """
        self.latest_frame = frame
        c_time = time.time()
        delta = c_time - self.p_time
        self.fps = 1.0 / delta if delta > 0 else 30.0
        self.p_time = c_time

        # -------------------------------------------------------------
        # 1. Validação de Entrada de Vídeo
        # -------------------------------------------------------------
        if frame is None or not HAS_CV2:
            self.athlete_detected = False
            self.is_dark = False
            self.frame_buffer.clear()
            return self._build_telemetry(status_override="Aguardando feed da câmera...")

        # Cálculo do brilho médio
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))

        # -------------------------------------------------------------
        # 2. Detecção MediaPipe Pose
        # -------------------------------------------------------------
        annotated_frame = frame.copy()
        landmarks = None
        has_valid_pose = False

        if self.landmarker is not None:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            detection_result = self.landmarker.detect(mp_image)

            if detection_result.pose_landmarks:
                raw_lms = detection_result.pose_landmarks[0]
                if is_valid_human_pose(raw_lms):
                    landmarks = raw_lms
                    has_valid_pose = True

        # Se não há pose e o brilho é quase zero (< 8.0), marca como escuro
        if not has_valid_pose and mean_brightness < 8.0:
            self.is_dark = True
            self.athlete_detected = False
            self.current_landmarks = None
            self.no_pose_consecutive += 1
            self.frame_buffer.clear()

            if c_time >= self.stroke_display_until:
                self.current_stroke_id = 3
                self.current_stroke_name = "Repouso"
                self.current_confidence = 0.0
                self.current_feedback = "Ambiente muito escuro - verifique a iluminação"
                self.failed_joints = []

            return self._build_telemetry()

        self.is_dark = False

        if has_valid_pose:
            self.current_landmarks = landmarks
            self.athlete_detected = True
            self.no_pose_consecutive = 0

            # Desenha os landmarks corporais
            if HAS_MEDIAPIPE:
                pose_style = drawing_styles.get_default_pose_landmarks_style()
                drawing_utils.draw_landmarks(
                    image=frame,
                    landmark_list=landmarks,
                    connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
                    landmark_drawing_spec=pose_style
                )
                drawing_utils.draw_landmarks(
                    image=annotated_frame,
                    landmark_list=landmarks,
                    connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
                    landmark_drawing_spec=pose_style
                )

            # Salva o frame anotado no buffer circular de 5 segundos (150 frames máx)
            self.replay_buffer.append(annotated_frame)

            # Centraliza landmarks pelo quadril e alimenta o buffer temporal
            centered_coords = process_landmarks_to_tensor(landmarks)
            self.frame_buffer.append(centered_coords)

            # ---------------------------------------------------------
            # 3. Inferência do Modelo Transformer com Cooldown e Janela de 60 Frames
            # ---------------------------------------------------------
            if len(self.frame_buffer) == 60:
                # Só executa nova classificação se já passou o tempo de cooldown
                if c_time >= self.stroke_cooldown_until:
                    input_data = np.stack(self.frame_buffer)
                    input_data = np.expand_dims(input_data, axis=0)

                    if HAS_TORCH:
                        input_tensor = torch.tensor(input_data, dtype=torch.float32).to(self.device)
                    else:
                        input_tensor = input_data

                    class_id, confidence = self.tennis_model(input_tensor)

                    # Gate cinemático calibrado: detecta tanto golpes amadores/compactos quanto profissionais,
                    # mantendo bloqueio absoluto a posturas de repouso estático (que possuem motion < 0.010).
                    buffer_arr = np.stack(self.frame_buffer)
                    wrist_motion = float((np.std(buffer_arr[:, 15, :]) + np.std(buffer_arr[:, 16, :])) / 2.0)
                    wrist_disp = float(np.ptp(buffer_arr[:, 15, :], axis=0).max() + np.ptp(buffer_arr[:, 16, :], axis=0).max())
                    elbow_motion = float((np.std(buffer_arr[:, 13, :]) + np.std(buffer_arr[:, 14, :])) / 2.0)
                    is_kinematically_active = (wrist_motion >= 0.020 and wrist_disp >= 0.08) or elbow_motion >= 0.018

                    # Se for golpe ativo (0=Forehand, 1=Backhand, 2=Saque) com confiança calibrada E movimento dinâmico real
                    if class_id in [0, 1, 2] and confidence >= 0.70 and is_kinematically_active:
                        stroke_names = {0: "Forehand", 1: "Backhand", 2: "Saque"}
                        self.current_stroke_id = int(class_id)
                        self.current_stroke_name = stroke_names[class_id]
                        self.current_confidence = float(confidence)
                        self.event_id += 1

                        # Fica visível na tela por 3.5 segundos sem piscar
                        self.stroke_display_until = c_time + 3.5
                        # Bloqueia novos disparos pelos próximos 2.5 segundos
                        self.stroke_cooldown_until = c_time + 2.5

                        # Avaliação biomecânica do golpe detectado
                        feedback_str, angles_dict, failed, quality_score, grade = rule_engine.evaluate_stroke(
                            class_id, landmarks, lateralidade=self.lateralidade
                        )
                        self.current_feedback = feedback_str
                        self.angles = {k: float(v) for k, v in angles_dict.items()}
                        self.failed_joints = failed

                        # Salva o vídeo de replay dos últimos 5 segundos com esqueleto
                        self._save_replay_clip(self.current_stroke_name, self.event_id)

                        # Atualiza motor de gamificação
                        self.game_engine.record_stroke(
                            self.current_stroke_id,
                            self.current_stroke_name,
                            self.current_confidence,
                            self.failed_joints,
                            self.angles,
                            quality_score,
                            grade
                        )

                        # Controle de LEDs no Arduino
                        if self.feedback_arduino is not None:
                            if failed:
                                for joint in failed:
                                    if joint in MAPA_LEDS:
                                        self.feedback_arduino.write(MAPA_LEDS[joint])
                                self.led_active = True
                            elif self.led_active:
                                self.feedback_arduino.write(b'R')
                                self.led_active = False

                        # Limpa parcialmente o buffer para não redisparar imediatamente
                        for _ in range(30):
                            if len(self.frame_buffer) > 0:
                                self.frame_buffer.popleft()

        else:
            # Nenhuma pessoa válida detectada no frame
            self.current_landmarks = None
            self.no_pose_consecutive += 1
            if self.no_pose_consecutive >= 5:
                self.athlete_detected = False
                self.frame_buffer.clear()

                # Se o tempo de exibição do golpe anterior já expirou, volta ao repouso
                if c_time >= self.stroke_display_until:
                    self.current_stroke_id = 3
                    self.current_stroke_name = "Repouso"
                    self.current_confidence = 0.0
                    self.current_feedback = "Posicione-se em frente à câmera"
                    self.failed_joints = []
                    if self.led_active and self.feedback_arduino is not None:
                        try:
                            self.feedback_arduino.write(b'R')
                            self.led_active = False
                        except Exception:
                            pass

        # -------------------------------------------------------------
        # 4. Expiração da Janela de Exibição de 3.5 segundos
        # -------------------------------------------------------------
        if c_time >= self.stroke_display_until:
            if self.athlete_detected:
                self.current_stroke_id = 3
                self.current_stroke_name = "Repouso"
                self.current_confidence = 0.0
                self.current_feedback = "Atleta em campo - pronto para golpear"
                self.failed_joints = []

        # Renderizar HUD Arcade sobre o frame se solicitado
        if render_hud and HAS_CV2 and frame is not None:
            self.hud.render(frame, self.game_engine.get_telemetry(), fps=self.fps)

        return self._build_telemetry()

    def _build_telemetry(self, status_override=None):
        feedback_text = status_override if status_override else self.current_feedback
        landmarks_data = None
        if self.athlete_detected and self.current_landmarks is not None:
            try:
                landmarks_data = [
                    [
                        round(float(lm.x), 4),
                        round(float(lm.y), 4),
                        round(float(getattr(lm, 'visibility', 1.0) if getattr(lm, 'visibility', None) is not None else 1.0), 3)
                    ]
                    for lm in self.current_landmarks
                ]
            except Exception:
                landmarks_data = None

        return {
            "timestamp": time.time(),
            "fps": round(self.fps, 1),
            "stroke_id": self.current_stroke_id,
            "stroke_name": self.current_stroke_name,
            "confidence": round(self.current_confidence, 2),
            "feedback": feedback_text,
            "failed_joints": self.failed_joints,
            "angles": self.angles,
            "led_active": self.led_active,
            "active_leds": self.failed_joints,
            "lateralidade": self.lateralidade,
            "athlete_detected": self.athlete_detected,
            "is_dark": self.is_dark,
            "event_id": self.event_id,
            "latest_replay_url": self.latest_replay_url,
            "latest_replay_filename": self.latest_replay_filename,
            "landmarks": landmarks_data,
            "game": self.game_engine.get_telemetry()
        }

    def get_jpeg_frame(self):
        """Retorna o frame atual codificado em JPEG para streaming MJPEG."""
        if not HAS_CV2 or self.latest_frame is None:
            return None
        ret, buffer = cv2.imencode('.jpg', self.latest_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if not ret:
            return None
        return buffer.tobytes()

    def close(self):
        if self.feedback_arduino is not None:
            try:
                self.feedback_arduino.write(b'R')
                self.feedback_arduino.close()
            except Exception:
                pass
        if self.landmarker is not None:
            self.landmarker.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="TenniSync - Arcade de Tênis e Visão Computacional")
    parser.add_argument("--source", type=str, default="0",
                        help="Índice da câmera (ex: 0) ou caminho para vídeo (.mp4).")
    parser.add_argument("--lateralidade", type=str, default="destro",
                        choices=["destro", "canhoto"], help="Lateralidade do tenista.")
    parser.add_argument("--headless", action="store_true",
                        help="Executa em segundo plano sem janela OpenCV.")
    args = parser.parse_args()

    engine = TennisSyncEngine(source=args.source, lateralidade=args.lateralidade)
    print("=" * 65)
    print(" [TenniSync] Pipeline de Tênis & Arcade Gamificado Iniciado")
    print(f" Fonte: {args.source} | Lateralidade: {args.lateralidade}")
    print(" Comandos da HUD: 'R' = Reiniciar Rally | 'Q' = Sair e Salvar Sessão")
    print("=" * 65)

    if args.headless or not HAS_CV2:
        try:
            while True:
                time.sleep(1)
                telemetry = engine.process_frame(None, render_hud=False)
                game = telemetry["game"]
                print(f"[STATUS] {telemetry['stroke_name']} | Atleta: {telemetry['athlete_detected']} | Rally: {game['rally_count']}", flush=True)
        except KeyboardInterrupt:
            print("\n[TenniSync] Encerrando serviço...")
        finally:
            engine.close()
    else:
        video_src = int(args.source) if args.source.isdigit() else args.source
        cap = cv2.VideoCapture(video_src)
        window_title = "TenniSync Arcade - [R] Reiniciar Rally | [Q] Sair"

        try:
            while cap.isOpened():
                success, frame = cap.read()
                if not success:
                    if not str(args.source).isdigit():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    time.sleep(0.05)
                    continue

                telemetry = engine.process_frame(frame, render_hud=True)
                cv2.imshow(window_title, frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('r') or key == ord('R'):
                    engine.reset_rally()
                    print("[TenniSync] Rally reiniciado pelo usuário!", flush=True)

        except KeyboardInterrupt:
            pass
        finally:
            cap.release()
            cv2.destroyAllWindows()
            saved_path = engine.game_engine.export_session_history()
            print(f"[TenniSync] Sessão exportada com sucesso em: {saved_path}")
            engine.close()

if __name__ == '__main__':
    main()
