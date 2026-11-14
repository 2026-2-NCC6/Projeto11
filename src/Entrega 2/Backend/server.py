import asyncio
import json
import threading
import time
import os
import sys
import base64

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

from contextlib import asynccontextmanager
from typing import Optional, List, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel

try:
    from logger import log_debug, log_info, log_warn, log_error, log_exception, log_sampled, get_recent_logs
except ImportError:
    from Backend.logger import log_debug, log_info, log_warn, log_error, log_exception, log_sampled, get_recent_logs

from pose_estimation import TennisSyncEngine
from auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    get_optional_user,
    verify_credentials,
    extract_token_from_request
)
from serial_manager import arduino_controller
from webrtc_service import WebRTCManager, DEFAULT_ICE_SERVERS

# Estado Global do Serviço
class ServerState:
    def __init__(self):
        self.camera_source = 0
        self.lateralidade = "destro"
        self.is_running = True
        self.camera_paused = False
        self.use_server_hardware_camera = False  # Prioriza câmera do cliente via WebRTC UDP
        self.engine = None
        self.cap = None
        self.last_client_frame_time = 0.0

        # Slot atômico Latest-Frame (Zero-Lag / Drop frame automático)
        self.incoming_client_frame = None
        self.incoming_frame_lock = threading.Lock()

        # WebRTC Manager
        self.webrtc_mgr = None
        self.camera_paused = False
        self.engine = None
        self.cap = None
        self.last_client_frame_time = 0.0

        replays_dir = os.path.join(BASE_DIR, "replays")
        init_replay_url = None
        init_replay_filename = None
        latest_mp4 = os.path.join(replays_dir, "replay_latest.mp4")
        if os.path.exists(latest_mp4) and os.path.getsize(latest_mp4) > 1000:
            init_replay_url = f"/api/replay/latest?t={int(os.path.getmtime(latest_mp4)*1000)}"
            init_replay_filename = "replay_latest.mp4"

        self.latest_telemetry = {
            "fps": 30.0,
            "stroke_id": 3,
            "stroke_name": "Repouso",
            "confidence": 0.0,
            "feedback": "Posicione-se em frente à câmera",
            "failed_joints": [],
            "angles": {"elbow_r": 120, "elbow_l": 120, "knee_r": 160, "knee_l": 160},
            "led_active": False,
            "active_leds": [],
            "lateralidade": "destro",
            "athlete_detected": False,
            "is_dark": False,
            "event_id": 0,
            "latest_replay_url": init_replay_url,
            "latest_replay_filename": init_replay_filename,
            "landmarks": None,
            "game": {
                "mode": "RALLY",
                "score": 0,
                "lives": 3,
                "max_lives": 3,
                "rally_count": 0,
                "best_rally": 0,
                "combo_streak": 0,
                "combo_multiplier": 1.0,
                "is_game_over": false if "false" in locals() else False,
                "accuracy": 100.0,
                "total_strokes": 0,
                "successful_strokes": 0,
                "faulty_strokes": 0,
                "last_grade": "NONE",
                "last_points": 0,
                "last_feedback": "Aguardando golpe válido",
                "last_stroke_name": "Repouso",
                "last_failed_joints": [],
                "xp": 0,
                "level": 1,
                "rank_title": "Iniciante",
                "xp_min": 0,
                "xp_next": 500,
                "xp_progress": 0.0,
                "unlocked_achievements": [],
                "new_achievement": None,
                "ball_challenge": {
                    "active": True,
                    "ball_id": 0,
                    "target_stroke_id": 0,
                    "target_stroke_name": "Forehand",
                    "target_x": 0.72,
                    "target_y": 0.68,
                    "flight_duration": 2.8,
                    "progress": 0.0,
                    "time_remaining": 2.8,
                    "status": "WAITING",
                    "hit_window_active": False,
                    "is_early": False
                }
            }
        }
        self.retrain_status = 'idle'
        self.retrain_log = ''
        self.latest_jpeg = None
        self.active_websockets = set()
        self.worker_thread = None

    def set_client_frame(self, frame):
        """Atualiza atomicamente o frame mais recente enviado pelo cliente (Latest-Frame-Wins)."""
        with self.incoming_frame_lock:
            self.incoming_client_frame = frame
            self.last_client_frame_time = time.time()

    def pop_incoming_frame(self):
        """Consome o frame mais recente sem travar a rede."""
        with self.incoming_frame_lock:
            frame = self.incoming_client_frame
            self.incoming_client_frame = None
            return frame

state = ServerState()

class SettingsPayload(BaseModel):
    lateralidade: str = "destro"
    source: str = "0"

class AuditActionPayload(BaseModel):
    action: str = "confirm"  # confirm, relabel, false_positive, discard
    target_class: str = "forehand"
    replay_filename: str | None = None

class LoginPayload(BaseModel):
    username: str
    password: str

class WebRtcOfferPayload(BaseModel):
    sdp: str
    type: str

class IotControlPayload(BaseModel):
    byte: Optional[str] = None
    joint: Optional[str] = None
    action: Optional[str] = "toggle"
    state: Optional[bool] = None

def video_worker():
    """
    Thread em segundo plano exclusiva que consome o Latest-Frame atômico do cliente
    e executa a inferência de IA sem race-condition e com latência mínima.
    """
    log_info("SYSTEM", "Inicializando motor TennisSyncEngine...")
    try:
        state.engine = TennisSyncEngine(source=state.camera_source, lateralidade=state.lateralidade)
        log_info("SYSTEM", "Motor TennisSyncEngine carregado com sucesso!")
    except Exception as e:
        log_exception("SYSTEM", "Erro ao inicializar TennisSyncEngine", e)
        state.engine = None

    # Frame JPEG fallback mínimo
    minimal_jpeg = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05'
        b'\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c'
        b'\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x10\x00\x10\x01\x01\x11\x00'
        b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03'
        b'\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9'
    )
    state.latest_jpeg = minimal_jpeg

    while state.is_running:
        if state.camera_paused:
            time.sleep(0.05)
            continue

        frame = None
        # 1. Prioridade absoluta: Frame recebido via UDP (WebRTC) ou WebSocket do Cliente
        incoming = state.pop_incoming_frame()
        if incoming is not None:
            frame = incoming
            state.last_client_frame_time = time.time()
        elif time.time() - state.last_client_frame_time < 3.0:
            # Cliente ativo transmitindo via UDP/WebRTC; dorme pequeno intervalo sem travar
            time.sleep(0.01)
            continue
        elif state.use_server_hardware_camera and HAS_CV2:
            # Modo Câmera Local do Servidor (OpenCV) apenas se explicitamente habilitado
            if state.cap is None or not state.cap.isOpened():
                try:
                    state.cap = cv2.VideoCapture(state.camera_source, cv2.CAP_DSHOW)
                    if not state.cap.isOpened():
                        state.cap = cv2.VideoCapture(state.camera_source)
                except Exception:
                    state.cap = None

            if state.cap is not None and state.cap.isOpened():
                success, raw_frame = state.cap.read()
                if success and raw_frame is not None:
                    frame = raw_frame
                else:
                    time.sleep(0.2)
        else:
            time.sleep(0.02)

        if state.engine is not None and frame is not None:
            try:
                telemetry = state.engine.process_frame(frame, render_hud=False)
                state.latest_telemetry = telemetry
            except Exception as e:
                log_exception("CAM/STREAM", "Erro em process_frame no worker de vídeo", e)

        if HAS_CV2 and frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                state.latest_jpeg = buffer.tobytes()

        time.sleep(0.01)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log_info("SYSTEM", "Servidor FastAPI TenniSync inicializado na porta 8000.")
    state.is_running = True
    state.webrtc_mgr = WebRTCManager(state)
    state.worker_thread = threading.Thread(target=video_worker, daemon=True)
    state.worker_thread.start()
    yield
    log_info("SYSTEM", "Encerrando servidor FastAPI TenniSync...")
    state.is_running = False
    if state.webrtc_mgr:
        try:
            await state.webrtc_mgr.close_all()
        except Exception:
            pass
    if state.cap:
        state.cap.release()
    if state.engine:
        state.engine.close()
    arduino_controller.close()

app = FastAPI(
    title="TenniSync Web Service API",
    description="Serviço Web desacoplado de Visão Computacional, IA e Biomecânica para tênis.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dist = os.path.abspath(os.path.join(BASE_DIR, "..", "Frontend", "dist"))

@app.get("/")
def root():
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "service": "TenniSync Web API",
        "version": "2.0.0",
        "architecture": "Desacoplada (Frontend em React, Backend em FastAPI)",
        "status": "online"
    }

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "lateralidade": state.lateralidade,
        "camera_source": state.camera_source,
        "camera_connected": (state.cap is not None and state.cap.isOpened()) or (time.time() - state.last_client_frame_time < 3.0),
        "client_streaming": time.time() - state.last_client_frame_time < 3.0,
        "arduino_connected": arduino_controller.is_connected,
        "latest_telemetry": state.latest_telemetry
    }

# ==============================================================================
# ENDPOINTS DE AUTENTICAÇÃO E SEGURANÇA (JWT + COOKIES + QUERY)
# ==============================================================================
@app.post("/api/auth/login")
def auth_login(payload: LoginPayload, response: Response):
    """Autentica o usuário com login e senha e emite token JWT com cookie seguro."""
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Verifique usuário e senha."
        )

    token = create_access_token({"sub": payload.username})
    # Define cookie para tags de mídia HTML5 (<img> e <video>)
    response.set_cookie(
        key="tennisync_token",
        value=token,
        httponly=False,
        max_age=86400,
        samesite="lax",
        secure=False
    )
    log_info("AUTH", f"Usuário '{payload.username}' autenticado com sucesso.")
    return {
        "status": "ok",
        "access_token": token,
        "token_type": "bearer",
        "username": payload.username
    }

@app.get("/api/auth/verify")
def auth_verify(user: dict = Depends(get_current_user)):
    """Valida se o token JWT atual ainda é válido."""
    return {"status": "ok", "user": user.get("sub", "user")}

@app.post("/api/auth/logout")
def auth_logout(response: Response):
    """Limpa o cookie de sessão."""
    response.delete_cookie(key="tennisync_token")
    return {"status": "ok", "message": "Sessão encerrada com sucesso."}

# ==============================================================================
# ENDPOINTS DE WEBRTC (STREAMING UDP DE VÍDEO E TELEMETRIA)
# ==============================================================================
@app.post("/api/webrtc/offer")
async def webrtc_offer(payload: WebRtcOfferPayload, user: dict = Depends(get_current_user)):
    """Recebe a oferta SDP do navegador e estabelece o canal de vídeo UDP."""
    if not state.webrtc_mgr:
        raise HTTPException(status_code=500, detail="WebRTC Manager não inicializado.")
    try:
        answer = await state.webrtc_mgr.handle_offer(payload.dict())
        return answer
    except Exception as e:
        log_exception("WEBRTC/UDP", "Erro ao processar oferta WebRTC", e)
        raise HTTPException(status_code=400, detail=f"Falha na negociação SDP: {e}")

@app.get("/api/webrtc/ice_servers")
def get_ice_servers():
    """Retorna servidores STUN/TURN públicos para travessia de NAT do cliente."""
    return {
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]},
            {"urls": ["stun:stun2.l.google.com:19302", "stun:stun.cloudflare.com:3478"]}
        ]
    }

# ==============================================================================
# ENDPOINTS DE CONTROLE DE HARDWARE IOT (ARDUINO UNO)
# ==============================================================================
@app.get("/api/iot/status")
def get_iot_status():
    """Retorna o estado das portas, LEDs acionados e modo do Arduino."""
    return arduino_controller.get_status()

@app.post("/api/iot/leds/control")
def control_iot_led(payload: IotControlPayload, user: dict = Depends(get_current_user)):
    """Aciona ou apaga individualmente LEDs no Arduino a partir da interface Web."""
    target = payload.byte or payload.joint
    if not target:
        raise HTTPException(status_code=400, detail="Parâmetro 'byte' (ex: 'A'-'L') ou 'joint' obrigatório.")

    if payload.action == "toggle" or payload.state is None:
        result = arduino_controller.toggle_led(target)
    else:
        desired = bool(payload.state or payload.action == "on")
        result = arduino_controller.trigger_led(target, desired)
    return result

@app.post("/api/iot/leds/reset")
def reset_iot_leds(user: dict = Depends(get_current_user)):
    """Apaga todos os 12 LEDs do protótipo físico."""
    return arduino_controller.reset_all_leds()

@app.post("/api/iot/leds/sweep")
def sweep_iot_leds(user: dict = Depends(get_current_user)):
    """Inicia teste de bancada varrendo os 12 atuadores sequencialmente."""
    return arduino_controller.run_sweep_test()

@app.get("/api/telemetry")
def get_telemetry():
    """Retorna o snapshot mais recente da telemetria e estado do jogo."""
    return state.latest_telemetry

@app.post("/api/settings")
def update_settings(payload: SettingsPayload):
    state.lateralidade = payload.lateralidade
    if state.engine:
        state.engine.set_lateralidade(payload.lateralidade)
    state.latest_telemetry["lateralidade"] = payload.lateralidade
    log_info("GAME-API", f"Configurações atualizadas: lateralidade={payload.lateralidade}")
    return {"message": "Configurações atualizadas", "lateralidade": state.lateralidade}

@app.post("/api/game/miss")
def report_game_miss():
    """Registra bola perdida ou erro de timing no jogo."""
    lives_remaining = 0
    if state.engine and hasattr(state.engine, 'game_engine'):
        ge = state.engine.game_engine
        ge.lives = max(0, ge.lives - 1)
        ge.combo_streak = 0
        ge.combo_multiplier = 1.0
        ge.ball_status = 'TOO_LATE'
        ge.last_result_time = time.time()
        ge.faulty_strokes += 1
        ge.last_feedback = "Bola perdida! Não golpeou a tempo (-1 Vida)"
        if ge.lives <= 0:
            ge.is_game_over = True
            ge.game_over_time = time.time()
        ge.save_profile()
        state.latest_telemetry["game"] = ge.get_telemetry()
        lives_remaining = ge.lives
        log_warn("GAME-API", "Bola perdida registrada via /api/game/miss", {
            "vidas_restantes": ge.lives,
            "status": ge.ball_status,
            "is_game_over": ge.is_game_over
        })
    return {"status": "ok", "lives": lives_remaining}

@app.post("/api/game/serve")
def trigger_game_serve():
    """Executa saque para colocar bola em jogo e arremessar para o adversário."""
    if state.engine and hasattr(state.engine, 'game_engine'):
        ge = state.engine.game_engine
        ge.ball_status = 'SERVED'
        ge.last_result_time = time.time()
        ge.score += 150
        ge.rally_count = max(1, ge.rally_count)
        ge.combo_streak = 1
        ge.last_feedback = "Saque potente! Bola arremessada para o adversário!"
        ge.save_profile()
        state.latest_telemetry["game"] = ge.get_telemetry()
        log_info("GAME-API", "Saque potente disparado no jogo", {"score": ge.score, "rally": ge.rally_count})
    return {"status": "ok"}

@app.post("/api/game/reset")
@app.post("/api/session/reset")
def reset_session():
    if state.engine:
        state.engine.reset_session()
        state.engine.reset_rally()
        if hasattr(state.engine, "game_engine"):
            state.latest_telemetry["game"] = state.engine.game_engine.get_telemetry()
    state.latest_telemetry["stroke_id"] = 3
    state.latest_telemetry["stroke_name"] = "Repouso"
    state.latest_telemetry["confidence"] = 0.0
    state.latest_telemetry["failed_joints"] = []
    state.latest_telemetry["led_active"] = False
    log_info("GAME-API", "Sessão e rally reiniciados com sucesso")
    return {"status": "ok", "message": "Sessão reiniciada com sucesso", "game": state.latest_telemetry.get("game", {})}

@app.get("/api/logs")
def get_system_logs(limit: int = 100, tag: str = None, min_level: str = None):
    """Retorna os logs mais recentes do buffer em memória do backend."""
    return {"logs": get_recent_logs(limit=limit, tag=tag, min_level=min_level)}

@app.api_route("/api/replay/latest", methods=["GET", "HEAD"])
def get_latest_replay():
    """Retorna o vídeo .mp4 dos 5 segundos do último golpe com sobreposição MediaPipe."""
    replays_dir = os.path.join(BASE_DIR, "replays")
    latest_path = os.path.join(replays_dir, "replay_latest.mp4")
    if os.path.exists(latest_path) and os.path.getsize(latest_path) > 1000:
        return FileResponse(
            latest_path,
            media_type="video/mp4",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Accept-Ranges": "bytes"
            }
        )
    return JSONResponse({"error": "Nenhum replay gravado ainda"}, status_code=404)

@app.api_route("/api/replays/{filename}", methods=["GET", "HEAD"])
def get_replay_file(filename: str):
    """Retorna um clipe de replay específico salvo na pasta de replays."""
    replays_dir = os.path.join(BASE_DIR, "replays")
    safe_name = os.path.basename(filename)
    file_path = os.path.join(replays_dir, safe_name)
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="video/mp4",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Accept-Ranges": "bytes"
            }
        )
    return JSONResponse({"error": "Replay não encontrado"}, status_code=404)

@app.post("/api/audit/label")
def handle_audit_label(payload: AuditActionPayload):
    """Salva o clipe limpo auditado diretamente na pasta oficial correspondente."""
    raw_dir = os.path.join(BASE_DIR, "dataset", "raw_videos")
    replays_dir = os.path.join(BASE_DIR, "replays")
    clean_latest = os.path.join(replays_dir, "clean_replay_latest.mp4")
    
    if payload.action == "discard":
        if state.engine and getattr(state.engine, 'feedback_arduino', None):
            try:
                state.engine.feedback_arduino.write(b'R')
            except Exception:
                pass
        return {"status": "ok", "message": "Clipe descartado sem salvar."}

    target_class = payload.target_class.lower()
    if payload.action == "false_positive":
        target_class = "repouso"

    if target_class not in ["forehand", "backhand", "saque", "repouso"]:
        return JSONResponse({"error": f"Classe desconhecida: {target_class}"}, status_code=400)

    target_dir = os.path.join(raw_dir, target_class)
    os.makedirs(target_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dest_filename = f"audit_{payload.action}_{timestamp}_{target_class}.mp4"
    dest_path = os.path.join(target_dir, dest_filename)

    src_path = clean_latest
    if payload.replay_filename:
        cand = os.path.join(replays_dir, payload.replay_filename.replace("replay_", "clean_"))
        if os.path.exists(cand):
            src_path = cand

    if not os.path.exists(src_path) or os.path.getsize(src_path) < 1000:
        src_path = os.path.join(replays_dir, "replay_latest.mp4")

    if os.path.exists(src_path) and os.path.getsize(src_path) > 1000:
        import shutil
        shutil.copyfile(src_path, dest_path)

        log_file = os.path.join(BASE_DIR, "data", "audit_log.json")
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "action": payload.action,
            "target_class": target_class,
            "filename": dest_filename,
            "source_clip": os.path.basename(src_path)
        }
        log_data = {"entries": []}
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                pass
        log_data.setdefault("entries", []).append(entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        if state.engine and getattr(state.engine, 'feedback_arduino', None):
            try:
                state.engine.feedback_arduino.write(b'R')
            except Exception:
                pass

        return {
            "status": "ok",
            "message": f"Vídeo salvo em raw_videos/{target_class}/{dest_filename}",
            "filename": dest_filename,
            "target_class": target_class
        }

    return JSONResponse({"error": "Nenhum arquivo de clipe encontrado para salvar"}, status_code=404)

@app.get("/api/audit/stats")
def get_audit_stats():
    """Retorna contadores de cada pasta e estatísticas de auditoria."""
    raw_dir = os.path.join(BASE_DIR, "dataset", "raw_videos")
    counts = {}
    for cat in ["forehand", "backhand", "saque", "repouso"]:
        p = os.path.join(raw_dir, cat)
        if os.path.exists(p):
            counts[cat] = len([f for f in os.listdir(p) if f.endswith(('.mp4', '.avi', '.mov'))])
        else:
            counts[cat] = 0

    log_file = os.path.join(BASE_DIR, "data", "audit_log.json")
    log_entries = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_entries = json.load(f).get("entries", [])
        except Exception:
            pass

    return {
        "dataset_counts": counts,
        "total_audited": len(log_entries),
        "recent_entries": log_entries[-10:],
        "retrain_status": state.retrain_status
    }

@app.post("/api/audit/retrain")
def trigger_retrain():
    """Executa compilação e retreino em segundo plano."""
    if state.retrain_status == "running":
        return {"status": "already_running", "message": "Treinamento já em andamento"}

    def run_training_worker():
        import subprocess
        state.retrain_status = "running"
        state.retrain_log = "Recompilando dataset...\n"
        try:
            p1 = subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_repertoire_dataset.py")], capture_output=True, text=True)
            state.retrain_log += p1.stdout
            if p1.returncode != 0:
                state.retrain_status = "error"
                state.retrain_log += f"\nErro na compilação: {p1.stderr}"
                return

            state.retrain_log += "\nRetreinando modelo Transformer...\n"
            p2 = subprocess.run([sys.executable, os.path.join(BASE_DIR, "train_model.py"), "--epochs", "25"], capture_output=True, text=True)
            state.retrain_log += p2.stdout
            if p2.returncode != 0:
                state.retrain_status = "error"
                state.retrain_log += f"\nErro no treino: {p2.stderr}"
                return

            if state.engine:
                state.engine.reload_model()

            state.retrain_status = "completed"
            state.retrain_log += "\nTreinamento concluído com sucesso e modelo recarregado!"
        except Exception as e:
            state.retrain_status = "error"
            state.retrain_log += f"\nExceção durante treino: {e}"

    t = threading.Thread(target=run_training_worker, daemon=True)
    t.start()
    return {"status": "started", "message": "Retreinamento iniciado em segundo plano"}

@app.get("/api/audit/retrain_status")
def get_retrain_status():
    return {"status": state.retrain_status, "log": state.retrain_log}

@app.post("/api/camera/pause")
def pause_camera():
    """Libera a webcam do servidor para que outro módulo possa usá-la com exclusividade."""
    state.camera_paused = True
    if state.cap is not None and state.cap.isOpened():
        try:
            state.cap.release()
        except Exception:
            pass
        state.cap = None
    print("[TenniSync Server] Webcam liberada com sucesso para módulo desktop.", flush=True)
    return {"status": "ok", "camera_paused": True, "message": "Webcam liberada"}

@app.post("/api/camera/resume")
def resume_camera():
    """Retoma a webcam no servidor web após término do módulo desktop."""
    state.camera_paused = False
    print("[TenniSync Server] Webcam retomada pelo servidor web.", flush=True)
    return {"status": "ok", "camera_paused": False, "message": "Webcam retomada"}

def mjpeg_generator():
    """Gera stream MJPEG compatível com tags <img> do navegador."""
    while state.is_running:
        if state.latest_jpeg is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + state.latest_jpeg + b'\r\n')
        time.sleep(0.04)

@app.get("/api/video_feed")
def video_feed():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    """
    WebSocket de alta velocidade para streaming de frames da webcam do navegador para a IA do Backend.
    Elimina qualquer incompatibilidade de hardware no Windows e permite feedback instantâneo.
    """
    await websocket.accept()
    log_info("WEBSOCKET", "Cliente conectado ao canal de vídeo (/ws/video)")
    try:
        while state.is_running:
            data = await websocket.receive()
            raw_bytes = None
            if "bytes" in data and data["bytes"]:
                raw_bytes = data["bytes"]
            elif "text" in data and data["text"]:
                try:
                    msg = json.loads(data["text"])
                    if "frame" in msg and msg["frame"]:
                        b64_str = msg["frame"]
                        if "," in b64_str:
                            b64_str = b64_str.split(",")[1]
                        raw_bytes = base64.b64decode(b64_str)
                except Exception as e:
                    log_warn("CAM/STREAM", f"Falha ao decodificar base64 de frame: {e}")

            if raw_bytes and HAS_CV2 and HAS_NUMPY:
                nparr = np.frombuffer(raw_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    # Deposita no slot atômico para o video_worker processar
                    state.set_client_frame(frame)
                    # Responde com o snapshot mais recente da telemetria
                    await websocket.send_text(json.dumps(state.latest_telemetry))
    except (WebSocketDisconnect, ConnectionResetError):
        log_info("WEBSOCKET", "Cliente desconectado do canal de vídeo (/ws/video)")
    except Exception as e:
        log_exception("WEBSOCKET", "Exceção inesperada no canal de vídeo (/ws/video)", e)

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    state.active_websockets.add(websocket)
    log_info("WEBSOCKET", "Cliente conectado à telemetria (/ws/telemetry)")
    try:
        while state.is_running:
            telemetry_data = json.dumps(state.latest_telemetry)
            await websocket.send_text(telemetry_data)

            try:
                incoming = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                msg = json.loads(incoming)
                if msg.get("type") == "config":
                    if "lateralidade" in msg:
                        state.lateralidade = msg["lateralidade"]
                        if state.engine:
                            state.engine.set_lateralidade(msg["lateralidade"])
                        log_info("GAME-API", f"Lateralidade atualizada via WebSocket: {state.lateralidade}")
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, ConnectionResetError):
        log_info("WEBSOCKET", "Cliente desconectado da telemetria (/ws/telemetry)")
    except Exception as e:
        log_exception("WEBSOCKET", "Exceção inesperada no canal de telemetria (/ws/telemetry)", e)
    finally:
        state.active_websockets.discard(websocket)

# Monta arquivos estáticos do Frontend compilado (se existirem) para servidor All-in-One
if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    log_info("SYSTEM", f"Frontend estático montado com sucesso a partir de {frontend_dist}")

if __name__ == "__main__":
    import uvicorn
    print("[TenniSync] Iniciando servidor Web na porta 8000...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
