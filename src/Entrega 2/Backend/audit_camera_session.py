from camera_utils import get_usb_camera_source, is_camera_blacklisted
"""
TenniSync - Módulo de Sessão de Auditoria Guiada, Qualificação Biomecânica e Treinamento
Permite executar movimentos com a câmera, acendimento em tempo real de LEDs no Arduino Uno (COM4),
pausa obrigatória a cada movimento com replay de 5 segundos em loop, auditoria (Esperado vs Previsto),
eliminação de falsos positivos (envio para repouso) e retreinamento automático em loop fechado.
"""

import os
import sys
import time
import json
import collections
import threading
import cv2
import numpy as np

# Configura caminhos do backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pose_estimation import TennisSyncEngine, create_compatible_videowriter, MAPA_LEDS
import rule_engine

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

def play_beep_async(freq, duration_ms):
    """Emite um beep sonoro sem travar o processamento da câmera."""
    if HAS_WINSOUND:
        t = threading.Thread(target=lambda: winsound.Beep(freq, duration_ms), daemon=True)
        t.start()

def request_server_camera_pause():
    """Notifica o servidor web FastAPI para liberar o handle da webcam."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8000/api/camera/pause", data=b'{}', headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=0.8)
        time.sleep(0.3)
    except Exception:
        pass

def request_server_camera_resume():
    """Notifica o servidor web FastAPI para retomar o uso da webcam."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8000/api/camera/resume", data=b'{}', headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=0.8)
    except Exception:
        pass

class AuditCameraSession:
    def __init__(self, source="0", lateralidade="destro", arduino_port="COM4"):
        self.source = str(get_usb_camera_source(source))
        self.lateralidade = lateralidade
        self.arduino_port = arduino_port
        
        # Diretórios oficiais
        self.raw_dir = os.path.join(BASE_DIR, "dataset", "raw_videos")
        self.log_file = os.path.join(BASE_DIR, "data", "audit_log.json")
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Garante as 4 pastas oficiais
        for cat in ["forehand", "backhand", "saque", "repouso"]:
            os.makedirs(os.path.join(self.raw_dir, cat), exist_ok=True)
            
        # Estatísticas da sessão
        self.stats = {
            "total_audited": 0,
            "confirmed": 0,
            "corrected": 0,
            "false_positives": 0,
            "discarded": 0,
            "new_videos": {
                "forehand": 0,
                "backhand": 0,
                "saque": 0,
                "repouso": 0
            }
        }
        self.load_audit_log()

        # Inicializa o Motor TenniSync
        print("==================================================================")
        print(" [TenniSync] Inicializando Motor de Visão e Auditoria...")
        print(f" - Câmera: {source} | Lateralidade: {lateralidade} | Arduino: {arduino_port}")
        print("==================================================================")
        self.engine = TennisSyncEngine(
            source=source,
            lateralidade=lateralidade,
            arduino_port=arduino_port
        )

        # Estado da Sessão: 'LIVE' ou 'AUDIT_PAUSE'
        self.state = "LIVE"
        
        # Dados do replay atual em auditoria
        self.current_event = None
        self.audit_frames = []
        self.clean_audit_frames = []
        self.replay_idx = 0
        self.action_banner = None
        self.action_banner_timer = 0
        self.last_event_id = 0
        self.led_persist_until = 0.0
        self.last_persist_failed = []

    def load_audit_log(self):
        """Carrega histórico acumulado de auditoria."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.stats["total_historical"] = data.get("total_audited", 0)
            except Exception:
                pass

    def save_audit_entry(self, action, target_class, predicted_class, confidence, quality_score, grade, feedback, filename):
        """Registra no log persistente de auditoria."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "target_class": target_class,
            "predicted_class": predicted_class,
            "confidence": float(confidence),
            "quality_score": float(quality_score),
            "grade": grade,
            "feedback": feedback,
            "filename": filename
        }
        
        data = {"entries": [], "summary": {}}
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data["entries"].append(entry)
        data["summary"] = self.stats
        
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Audit Log] Erro ao gravar log: {e}")

    def save_clean_clip(self, target_class, prefix="audit"):
        """Salva a sequência de frames limpos na pasta oficial da classe."""
        if not self.clean_audit_frames or len(self.clean_audit_frames) < 15:
            # Fallback para frames anotados se os limpos estiverem vazios
            frames_to_save = self.audit_frames
        else:
            frames_to_save = self.clean_audit_frames

        if not frames_to_save:
            return None

        h, w = frames_to_save[0].shape[:2]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}_{target_class}.mp4"
        out_path = os.path.join(self.raw_dir, target_class, filename)

        fps = max(15.0, min(30.0, getattr(self.engine, 'fps', 30.0)))
        writer = create_compatible_videowriter(out_path, fps, w, h)
        if writer is not None and writer.isOpened():
            for f in frames_to_save:
                writer.write(f)
            writer.release()
            print(f"[Auditoria] Vídeo limpo gravado com sucesso: {out_path} ({len(frames_to_save)} frames)")
            return filename
        else:
            print(f"[Auditoria] Erro ao criar VideoWriter para: {out_path}")
            return None

    def trigger_audit_pause(self, telemetry):
        """Pausa a câmera obrigatoriamente e prepara o loop de replay com os dados coletados."""
        self.state = "AUDIT_PAUSE"
        self.audit_frames = list(self.engine.replay_buffer)
        self.clean_audit_frames = list(self.engine.clean_replay_buffer)
        self.replay_idx = 0
        
        # Copia dados do evento
        stroke = telemetry.get("stroke_name", "Golpe")
        conf = telemetry.get("confidence", 0.0)
        grade = telemetry.get("grade", "GOOD")
        qscore = telemetry.get("quality_score", 85.0)
        feedback = telemetry.get("feedback", "Execução normal")
        failed = telemetry.get("failed_joints", [])

        self.current_event = {
            "stroke": stroke,
            "confidence": conf,
            "grade": grade,
            "quality_score": qscore,
            "feedback": feedback,
            "failed_joints": failed
        }
        self.last_persist_failed = list(failed)
        self.led_persist_until = time.time() + 8.0
        
        # Beep sonoro de notificação de pausa para auditoria
        play_beep_async(900, 180)
        print("\n" + "="*65)
        print(f" [PAUSA DE AUDITORIA] Golpe Detectado: {stroke.upper()} ({conf*100:.1f}%)")
        print(f" Nota Biomecânica: {grade} | Qualidade: {qscore:.1f}/100")
        print(f" Diagnóstico: {feedback}")
        if failed:
            print(f" LEDs Físicos Acesos: {', '.join(failed)}")
        else:
            print(" LEDs: Nenhum erro angular (Movimento Limpo)")
        print(" Comandos: [ENTER] Confirmar | [1] Forehand | [2] Backhand | [3] Saque | [4/F] Falso Positivo | [D] Descartar")
        print("="*65 + "\n")

    def draw_live_hud(self, frame, telemetry=None):
        """Desenha a barra superior informativa e o banner de golpe detectado durante a captura ao vivo."""
        h, w = frame.shape[:2]
        telemetry = telemetry or {}
        overlay = frame.copy()
        
        # Faixa superior translúcida
        cv2.rectangle(overlay, (0, 0), (w, 64), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)

        # Título
        cv2.putText(frame, "TenniSync - Sessao de Auditoria Guiada", (16, 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (56, 189, 248), 2, cv2.LINE_AA)
        
        # Placar da sessão
        stats_str = f"Auditados: {self.stats['total_audited']} | FH: {self.stats['new_videos']['forehand']} | BH: {self.stats['new_videos']['backhand']} | SQ: {self.stats['new_videos']['saque']} | Falsos Pos (Repouso): {self.stats['new_videos']['repouso']}"
        cv2.putText(frame, stats_str, (16, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (226, 232, 240), 1, cv2.LINE_AA)

        # Dica rápida no canto inferior
        cv2.putText(frame, "[P] Pausar e Auditar Ultimos 5s  |  [R] Gravar Repouso (5s)  |  [Q] Finalizar Sessao",
                    (16, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)

        # Banner de ação recente (se houver)
        if self.action_banner and time.time() < self.action_banner_timer:
            b_overlay = frame.copy()
            cv2.rectangle(b_overlay, (w//2 - 250, 75), (w//2 + 250, 115), (16, 185, 129), -1)
            cv2.addWeighted(b_overlay, 0.85, frame, 0.15, 0, frame)
            cv2.putText(frame, self.action_banner, (w//2 - 230, 102),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        # Banner proeminente de golpe detectado ao vivo
        stroke_name = telemetry.get("stroke_name", "Repouso")
        stroke_id = telemetry.get("stroke_id", 3)
        conf = telemetry.get("confidence", 0.0) * 100
        grade = telemetry.get("grade", "GOOD")
        if stroke_id in [0, 1, 2]:
            s_overlay = frame.copy()
            bw = 480
            bx1 = (w - bw) // 2
            cv2.rectangle(s_overlay, (bx1, 75), (bx1 + bw, 130), (15, 23, 42), -1)
            cv2.rectangle(s_overlay, (bx1, 75), (bx1 + bw, 130), (56, 189, 248), 2)
            cv2.addWeighted(s_overlay, 0.85, frame, 0.15, 0, frame)

            cv2.putText(frame, f"GOLPE DETECTADO: {stroke_name.upper()} ({conf:.0f}%)", (bx1 + 16, 102),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (56, 189, 248), 2, cv2.LINE_AA)
            grade_col = (74, 222, 128) if grade in ["PERFECT", "GOOD"] else (248, 113, 113)
            cv2.putText(frame, f"Nota: {grade}", (bx1 + bw - 135, 102),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, grade_col, 2, cv2.LINE_AA)
            cv2.putText(frame, "Pausando para auditoria...", (bx1 + 16, 122),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (148, 163, 184), 1, cv2.LINE_AA)

        # Desenha o corpo com os 12 LEDs no canto superior direito (mantém persistência ativa)
        failed = getattr(self.engine, "failed_joints", [])
        if not failed and time.time() < self.led_persist_until:
            failed = self.last_persist_failed
        self.draw_virtual_body_leds(frame, failed_joints=failed, x=w - 230, y=75, w=215, h=330)

    def draw_virtual_body_leds(self, frame, failed_joints=None, x=1040, y=75, w=220, h=330):
        """Desenha na tela o corpo humano virtual com os 12 LEDs posicionados nas articulações."""
        failed_joints = failed_joints or []
        h_f, w_f = frame.shape[:2]
        
        if x + w > w_f:
            x = w_f - w - 10

        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (15, 23, 42), -1)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (56, 189, 248), 1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Cabeçalho do Card
        cv2.putText(frame, "CORPO IoT (12 LEDs)", (x + 18, y + 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (251, 191, 36), 2, cv2.LINE_AA)
        
        has_arduino = getattr(self.engine, "feedback_arduino", None) is not None
        status_txt = "Arduino: COM4" if has_arduino else "Arduino: VIRTUAL"
        status_col = (52, 211, 153) if has_arduino else (56, 189, 248)
        cv2.putText(frame, status_txt, (x + 18, y + 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, status_col, 1, cv2.LINE_AA)

        # Centro do manequim anatômico
        bx = x + w // 2
        by = y + 160

        # 1. Desenha o esqueleto / silhueta do corpo em linhas sutis
        # Cabeça
        cv2.circle(frame, (bx, by - 80), 14, (71, 85, 105), 2)
        # Pescoço e Coluna
        cv2.line(frame, (bx, by - 66), (bx, by - 50), (71, 85, 105), 2)
        cv2.line(frame, (bx, by - 50), (bx, by + 15), (71, 85, 105), 2)
        # Ombros
        cv2.line(frame, (bx - 36, by - 50), (bx + 36, by - 50), (71, 85, 105), 2)
        # Braço Direito (Direita do atleta = Esquerda na visão frontal da câmera)
        cv2.line(frame, (bx - 36, by - 50), (bx - 55, by - 12), (71, 85, 105), 2)
        cv2.line(frame, (bx - 55, by - 12), (bx - 70, by + 22), (71, 85, 105), 2)
        # Braço Esquerdo
        cv2.line(frame, (bx + 36, by - 50), (bx + 55, by - 12), (71, 85, 105), 2)
        cv2.line(frame, (bx + 55, by - 12), (bx + 70, by + 22), (71, 85, 105), 2)
        # Pelve / Quadril
        cv2.line(frame, (bx - 22, by + 15), (bx + 22, by + 15), (71, 85, 105), 2)
        # Perna Direita
        cv2.line(frame, (bx - 22, by + 15), (bx - 26, by + 65), (71, 85, 105), 2)
        cv2.line(frame, (bx - 26, by + 65), (bx - 28, by + 115), (71, 85, 105), 2)
        # Perna Esquerda
        cv2.line(frame, (bx + 22, by + 15), (bx + 26, by + 65), (71, 85, 105), 2)
        cv2.line(frame, (bx + 26, by + 65), (bx + 28, by + 115), (71, 85, 105), 2)

        # 2. Definição precisa dos 12 LEDs (conforme firmware_leds.ino)
        # (ID, Letra, Pino, X, Y, Offset_Texto)
        led_nodes = [
            ("ombro_dir",     "A", 2,  bx - 36, by - 50, (-18, -4)),
            ("ombro_esq",     "B", 3,  bx + 36, by - 50, (8, -4)),
            ("cotovelo_dir",  "C", 4,  bx - 55, by - 12, (-18, 4)),
            ("cotovelo_esq",  "D", 5,  bx + 55, by - 12, (8, 4)),
            ("pulso_dir",     "E", 6,  bx - 70, by + 22, (-18, 4)),
            ("pulso_esq",     "F", 7,  bx + 70, by + 22, (8, 4)),
            ("quadril_dir",   "G", 8,  bx - 22, by + 15, (-16, 4)),
            ("quadril_esq",   "H", 9,  bx + 22, by + 15, (8, 4)),
            ("joelho_dir",    "I", 10, bx - 26, by + 65, (-16, 4)),
            ("joelho_esq",    "J", 11, bx + 26, by + 65, (8, 4)),
            ("tornozelo_dir", "K", 12, bx - 28, by + 115, (-16, 4)),
            ("tornozelo_esq", "L", 13, bx + 28, by + 115, (8, 4)),
        ]

        # 3. Renderiza cada LED
        for j_id, letter, pin, lx, ly, (tx, ty) in led_nodes:
            is_active = j_id in failed_joints
            if is_active:
                # LED Aceso: Vermelho pulsante brilhante com halo
                cv2.circle(frame, (lx, ly), 11, (0, 0, 255), 2)
                cv2.circle(frame, (lx, ly), 6, (0, 69, 255), -1)
                cv2.circle(frame, (lx, ly), 3, (255, 255, 255), -1)
                cv2.putText(frame, f"{letter}", (lx + tx, ly + ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                # LED Apagado: Verde sutil com letra em cinza
                cv2.circle(frame, (lx, ly), 5, (52, 211, 153), -1)
                cv2.circle(frame, (lx, ly), 6, (15, 23, 42), 1)
                cv2.putText(frame, f"{letter}", (lx + tx, ly + ty),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.32, (148, 163, 184), 1, cv2.LINE_AA)

        # 4. Rodapé do Card
        if failed_joints:
            active_letters = [l for j, l, _, _, _, _ in led_nodes if j in failed_joints]
            alert_str = f"ACESO: {', '.join(active_letters)}"
            cv2.putText(frame, alert_str, (x + 12, y + h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "Todos os LEDs apagados", (x + 18, y + h - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (52, 211, 153), 1, cv2.LINE_AA)

    def draw_audit_overlay(self, frame):
        """Desenha o card completo e elegante de auditoria durante o replay de 5s em loop."""
        h, w = frame.shape[:2]
        overlay = frame.copy()
        
        # Card semi-transparente centralizado
        card_w = min(720, w - 40)
        card_h = 330
        x1 = (w - card_w) // 2
        y1 = 20
        x2 = x1 + card_w
        y2 = y1 + card_h

        cv2.rectangle(overlay, (x1, y1), (x2, y2), (10, 15, 29), -1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (56, 189, 248), 2)
        cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)

        evt = self.current_event or {}
        stroke = evt.get("stroke", "GOLPE").upper()
        conf = evt.get("confidence", 0.0) * 100
        grade = evt.get("grade", "GOOD")
        qscore = evt.get("quality_score", 85.0)
        feedback = evt.get("feedback", "Execucao dentro do padrao biomecanico")
        failed = evt.get("failed_joints", [])

        # Cabeçalho do Card
        cv2.putText(frame, "=== MODO AUDITORIA - REPLAY EM PAUSA (5s) ===", (x1 + 20, y1 + 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (251, 191, 36), 2, cv2.LINE_AA)
        
        # Linha 1: Diagnóstico da IA
        cv2.putText(frame, f"Previsao da IA: {stroke} ({conf:.1f}% de confianca)", (x1 + 20, y1 + 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Linha 2: Qualidade Biomecânica
        grade_color = (74, 222, 128) if grade in ["PERFECT", "GOOD"] else (248, 113, 113)
        cv2.putText(frame, f"Qualidade Biomecanica: {grade} ({qscore:.1f} pts)", (x1 + 20, y1 + 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, grade_color, 2, cv2.LINE_AA)
        
        # Linha 3: Feedback Descritivo
        cv2.putText(frame, f"Diagnostico: {feedback}", (x1 + 20, y1 + 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (226, 232, 240), 1, cv2.LINE_AA)

        # Linha 4: Hardware IoT Arduino
        if failed:
            led_str = f"LEDs Fisicos Acesos no Arduino: {', '.join(failed)}"
            led_col = (248, 113, 113)
        else:
            led_str = "LEDs Arduino: Nenhum desvio angular (Trajetoria Correta)"
            led_col = (52, 211, 153)
        cv2.putText(frame, led_str, (x1 + 20, y1 + 158),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, led_col, 1, cv2.LINE_AA)

        # Linha divisória
        cv2.line(frame, (x1 + 15, y1 + 175), (x2 - 15, y1 + 175), (71, 85, 105), 1)

        # Linha 5: Controles de Teclado
        cv2.putText(frame, f"[ENTER / C] CONFIRMAR COMO {stroke}", (x1 + 20, y1 + 205),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (52, 211, 153), 2, cv2.LINE_AA)

        cv2.putText(frame, "[1] Forehand      [2] Backhand      [3] Saque", (x1 + 20, y1 + 238),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.54, (56, 189, 248), 2, cv2.LINE_AA)

        cv2.putText(frame, "[4 / F] MARCAR COMO FALSO POSITIVO (ERA REPOUSO)", (x1 + 20, y1 + 272),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (251, 146, 60), 2, cv2.LINE_AA)

        cv2.putText(frame, "[D] Descartar Clipe          [Q] Sair da Sessao", (x1 + 20, y1 + 305),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (148, 163, 184), 1, cv2.LINE_AA)

        # Também exibe o corpo anatômico dos LEDs ao lado do card durante o replay
        self.draw_virtual_body_leds(frame, failed_joints=failed, x=w - 230, y=75, w=215, h=330)

    def handle_audit_action(self, action_type, chosen_class=None):
        """Processa a decisão do usuário durante a auditoria."""
        evt = self.current_event or {}
        stroke_pred = evt.get("stroke", "forehand").lower()
        conf = evt.get("confidence", 0.0)
        grade = evt.get("grade", "GOOD")
        qscore = evt.get("quality_score", 85.0)
        feedback = evt.get("feedback", "")

        target_class = chosen_class if chosen_class else stroke_pred
        
        # Mapeamento do nome amigável
        class_clean_map = {
            "forehand": "forehand",
            "backhand": "backhand",
            "saque": "saque",
            "repouso": "repouso"
        }
        target_class = class_clean_map.get(target_class, "forehand")

        if action_type == "confirm":
            fname = self.save_clean_clip(target_class, prefix="audit_ok")
            self.stats["total_audited"] += 1
            self.stats["confirmed"] += 1
            self.stats["new_videos"][target_class] += 1
            self.action_banner = f"CONFIRMADO: {target_class.upper()} salvo no dataset!"
            self.action_banner_timer = time.time() + 3.0
            play_beep_async(1200, 160)
            self.save_audit_entry("confirm", target_class, stroke_pred, conf, qscore, grade, feedback, fname)

        elif action_type == "relabel":
            fname = self.save_clean_clip(target_class, prefix="audit_corrected")
            self.stats["total_audited"] += 1
            self.stats["corrected"] += 1
            self.stats["new_videos"][target_class] += 1
            self.action_banner = f"CORRIGIDO: Salvo como {target_class.upper()} no dataset!"
            self.action_banner_timer = time.time() + 3.0
            play_beep_async(1000, 180)
            self.save_audit_entry("relabel", target_class, stroke_pred, conf, qscore, grade, feedback, fname)

        elif action_type == "false_positive":
            target_class = "repouso"
            fname = self.save_clean_clip(target_class, prefix="audit_falso_positivo")
            self.stats["total_audited"] += 1
            self.stats["false_positives"] += 1
            self.stats["new_videos"]["repouso"] += 1
            self.action_banner = "FALSO POSITIVO ELIMINADO: Enviado para repouso/!"
            self.action_banner_timer = time.time() + 3.0
            play_beep_async(850, 120)
            play_beep_async(1150, 180)
            self.save_audit_entry("false_positive", "repouso", stroke_pred, conf, qscore, grade, feedback, fname)

        elif action_type == "discard":
            self.stats["discarded"] += 1
            self.action_banner = "Clipe descartado sem salvar."
            self.action_banner_timer = time.time() + 2.0
            play_beep_async(600, 140)

        # Apaga os LEDs no Arduino (Comando 'R')
        if getattr(self.engine, "feedback_arduino", None) is not None:
            try:
                self.engine.feedback_arduino.write(b'R')
            except Exception:
                pass

        # Limpa o buffer de eventos e retorna à câmera ao vivo
        self.state = "LIVE"
        self.current_event = None
        self.audit_frames = []
        self.clean_audit_frames = []
        print(f"[Auditoria] Ação concluída ({action_type}). Retornando à câmera ao vivo...")

    def run(self):
        """Loop principal da sessão de auditoria e captura."""
        window_name = "TenniSync - Auditoria e Qualificacao de Movimento"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

        # 1. Solicita liberação da webcam ao servidor web local se estiver ativo
        request_server_camera_pause()

        # 2. Abre câmera
        source_idx = int(self.source) if self.source.isdigit() else self.source
        cap = cv2.VideoCapture(source_idx)
        if not cap.isOpened() and sys.platform == 'win32' and isinstance(source_idx, int):
            cap = cv2.VideoCapture(source_idx, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not cap.isOpened():
            print(f"[Erro Fatal] Não foi possível abrir a câmera {self.source}")
            return

        print("\n" + "="*65)
        print(" [SESSÃO INICIADA] Posicione-se a 2m - 3.5m da câmera.")
        print(" O sistema analisará a trajetória contínua e acenderá os LEDs.")
        print(" Ao final de cada movimento, a tela pausará com o replay de 5s.")
        print("="*65 + "\n")
        fail_count = 0

        try:
            while True:
                if self.state == "LIVE":
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        fail_count += 1
                        # Desenha tela de espera com chamada ativa a waitKey para evitar que o Windows marque como 'Não respondendo'
                        waiting_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                        cv2.putText(waiting_frame, "TenniSync: Conectando a webcam...", (380, 330),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, (56, 189, 248), 2, cv2.LINE_AA)
                        cv2.putText(waiting_frame, "Aguarde enquanto a camera e inicializada com exclusividade.", (330, 375),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (148, 163, 184), 1, cv2.LINE_AA)
                        cv2.putText(waiting_frame, "Pressione [Q] para sair se necessario.", (440, 420),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (100, 116, 139), 1, cv2.LINE_AA)
                        cv2.imshow(window_name, waiting_frame)
                        k = cv2.waitKey(30) & 0xFF
                        if k in [ord('q'), ord('Q')]:
                            break
                        if fail_count % 20 == 0:
                            cap.release()
                            time.sleep(0.3)
                            request_server_camera_pause()
                            cap = cv2.VideoCapture(source_idx)
                        continue
                    fail_count = 0

                    # Processa frame sem o HUD do jogo arcade (sem rally, sem pontos, sem vidas)
                    telemetry = self.engine.process_frame(frame, render_hud=False)
                    annotated_frame = frame
                    self.draw_live_hud(annotated_frame, telemetry=telemetry)

                    # Gatilho imediato de pausa e replay: quando event_id incrementa para Forehand, Backhand ou Saque
                    curr_event_id = telemetry.get("event_id", 0)
                    stroke_id = telemetry.get("stroke_id", 3)
                    has_new_event = telemetry.get("new_event", False) or (curr_event_id > self.last_event_id and stroke_id in [0, 1, 2])
                    if has_new_event:
                        self.last_event_id = curr_event_id
                        self.trigger_audit_pause(telemetry)

                    cv2.imshow(window_name, annotated_frame)
                    key = cv2.waitKey(1) & 0xFF

                    if key in [ord('q'), ord('Q')]:
                        print("[Sessão] Solicitado encerramento pelo usuário...")
                        break
                    elif key in [ord('p'), ord('P')]:
                        # Pausa manual forçada para auditar o que acabou de ser feito
                        mock_telemetry = {
                            "stroke_name": getattr(self.engine, "current_stroke", "Movimento"),
                            "confidence": getattr(self.engine, "current_confidence", 0.85),
                            "grade": "GOOD",
                            "quality_score": 80.0,
                            "feedback": "Pausa manual solicitada pelo usuario",
                            "failed_joints": []
                        }
                        self.trigger_audit_pause(mock_telemetry)
                    elif key in [ord('r'), ord('R')]:
                        # Grava os últimos 5 segundos direto como repouso sem pausar
                        self.audit_frames = list(self.engine.replay_buffer)
                        self.clean_audit_frames = list(self.engine.clean_replay_buffer)
                        self.handle_audit_action("false_positive", chosen_class="repouso")

                elif self.state == "AUDIT_PAUSE":
                    # MODO PAUSA OBRIGATÓRIA: loop dos últimos 5 segundos
                    if not self.audit_frames:
                        self.state = "LIVE"
                        continue

                    frame_idx = self.replay_idx % len(self.audit_frames)
                    current_frame = self.audit_frames[frame_idx].copy()
                    self.replay_idx += 1

                    self.draw_audit_overlay(current_frame)
                    cv2.imshow(window_name, current_frame)

                    # Intervalo para reprodução a ~25 FPS
                    key = cv2.waitKey(40) & 0xFF

                    if key in [13, ord('c'), ord('C')]:  # ENTER ou C
                        self.handle_audit_action("confirm")
                    elif key == ord('1'):
                        self.handle_audit_action("relabel", chosen_class="forehand")
                    elif key == ord('2'):
                        self.handle_audit_action("relabel", chosen_class="backhand")
                    elif key == ord('3'):
                        self.handle_audit_action("relabel", chosen_class="saque")
                    elif key in [ord('4'), ord('f'), ord('F')]:
                        self.handle_audit_action("false_positive", chosen_class="repouso")
                    elif key in [ord('d'), ord('D')]:
                        self.handle_audit_action("discard")
                    elif key in [ord('q'), ord('Q')]:
                        print("[Sessão] Solicitado encerramento durante a auditoria...")
                        break

        finally:
            cap.release()
            cv2.destroyAllWindows()
            request_server_camera_resume()
            if getattr(self.engine, "feedback_arduino", None) is not None:
                try:
                    self.engine.feedback_arduino.write(b'R')
                    self.engine.feedback_arduino.close()
                except Exception:
                    pass

        self.show_summary_and_offer_retrain()

    def show_summary_and_offer_retrain(self):
        """Exibe o sumário final e oferece o retreinamento automático em loop fechado."""
        print("\n" + "="*65)
        print("                  SESSÃO DE AUDITORIA FINALIZADA")
        print("="*65)
        print(f" Total de Movimentos Auditados: {self.stats['total_audited']}")
        print(f"  - Confirmados (Previsto = Correto): {self.stats['confirmed']}")
        print(f"  - Corrigidos Manualmente:           {self.stats['corrected']}")
        print(f"  - Falsos Positivos (Para Repouso):  {self.stats['false_positives']}")
        print(f"  - Descartados:                      {self.stats['discarded']}")
        print("\n Novos Vídeos Adicionados ao Dataset:")
        print(f"  - Forehand: {self.stats['new_videos']['forehand']}")
        print(f"  - Backhand: {self.stats['new_videos']['backhand']}")
        print(f"  - Saque:    {self.stats['new_videos']['saque']}")
        print(f"  - Repouso:  {self.stats['new_videos']['repouso']}")
        print("="*65)

        total_new = sum(self.stats["new_videos"].values())
        if total_new > 0:
            print(f"\nForam gravados {total_new} novos clipes limpos para treinamento.")
            ans = input("\nDeseja retreinar o modelo de IA agora com esses novos dados? [S/n] (Padrao: S): ").strip().lower()
            if ans in ["", "s", "sim", "y", "yes"]:
                self.trigger_retrain()
            else:
                print("\n[Aviso] Retreino ignorado. Os vídeos permanecerão salvos nas 4 pastas para o próximo treino.")
        else:
            print("\nNenhum vídeo novo foi gravado nesta sessão. Não é necessário retreinar.")

    def trigger_retrain(self):
        """Executa a compilação do dataset e o retreino do TennisTransformer."""
        import subprocess
        print("\n" + "#"*65)
        print(" [PASSO 1/2] Recompilando o Dataset com os Novos Vídeos Auditados...")
        print("#"*65)
        ret1 = subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_repertoire_dataset.py")])
        if ret1.returncode != 0:
            print("[Erro] Falha ao recompilar o dataset.")
            return

        print("\n" + "#"*65)
        print(" [PASSO 2/2] Retreinando o Modelo TennisTransformer (Loop Fechado)...")
        print("#"*65)
        ret2 = subprocess.run([sys.executable, os.path.join(BASE_DIR, "train_model.py"), "--epochs", "25"])
        if ret2.returncode == 0:
            print("\n" + "="*65)
            print(" [SUCESSO TOTAL] Modelo retreinado e pesos atualizados com sucesso!")
            print(" O novo cérebro da IA agora incorpora perfeitamente suas correções.")
            print("="*65 + "\n")
        else:
            print("[Erro] Falha ao treinar o modelo.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TenniSync - Sessão de Auditoria Guiada e Treinamento")
    parser.add_argument("--source", type=str, default=None, help="Índice da câmera (padrão: 0)")
    parser.add_argument("--lateralidade", type=str, default="destro", choices=["destro", "canhoto"], help="Lateralidade do atleta")
    parser.add_argument("--arduino_port", type=str, default="COM4", help="Porta serial do Arduino Uno (padrão: COM4)")
    args = parser.parse_args()

    session = AuditCameraSession(
        source=args.source,
        lateralidade=args.lateralidade,
        arduino_port=args.arduino_port
    )
    session.run()
