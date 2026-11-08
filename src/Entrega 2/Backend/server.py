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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from pose_estimation import TennisSyncEngine

# Estado Global do Serviço
class ServerState:
    def __init__(self):
        self.camera_source = 0
        self.lateralidade = "destro"
        self.is_running = True
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
                "new_achievement": None
            }
        }
        self.latest_jpeg = None
        self.active_websockets = set()
        self.worker_thread = None

state = ServerState()

class SettingsPayload(BaseModel):
    lateralidade: str = "destro"
    source: str = "0"

def video_worker():
    """Thread em segundo plano que executa a captura de vídeo e inferência contínua."""
    print("[TenniSync Server] Iniciando motor TennisSyncEngine...", flush=True)
    try:
        state.engine = TennisSyncEngine(source=state.camera_source, lateralidade=state.lateralidade)
    except Exception as e:
        print(f"[TenniSync Server] Erro ao inicializar TennisSyncEngine: {e}", flush=True)
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
        # Se o navegador está enviando frames via WebSocket (< 2.0s atrás),
        # deixa o navegador ser a fonte de vídeo e não bloqueia a câmera via OpenCV
        if time.time() - state.last_client_frame_time < 2.0:
            if state.cap is not None and state.cap.isOpened():
                try:
                    state.cap.release()
                except Exception:
                    pass
                state.cap = None
            time.sleep(0.04)
            continue

        # Modo Câmera do Backend (OpenCV autônomo)
        frame = None
        if HAS_CV2:
            if state.cap is None or not state.cap.isOpened():
                try:
                    # Tenta DirectShow primeiro para evitar exclusividade MSMF no Windows
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
                    time.sleep(0.5)

        if state.engine is not None and frame is not None:
            try:
                telemetry = state.engine.process_frame(frame, render_hud=True)
                state.latest_telemetry = telemetry
            except Exception as e:
                print(f"[TenniSync Server] Erro em process_frame: {e}", flush=True)

        if HAS_CV2 and frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                state.latest_jpeg = buffer.tobytes()

        time.sleep(0.033)

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.is_running = True
    state.worker_thread = threading.Thread(target=video_worker, daemon=True)
    state.worker_thread.start()
    yield
    state.is_running = False
    if state.cap:
        state.cap.release()
    if state.engine:
        state.engine.close()

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

@app.get("/")
def root():
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
        "camera_connected": (state.cap is not None and state.cap.isOpened()) or (time.time() - state.last_client_frame_time < 2.0),
        "client_streaming": time.time() - state.last_client_frame_time < 2.0,
        "arduino_connected": state.engine.feedback_arduino is not None if state.engine else False,
        "latest_telemetry": state.latest_telemetry
    }

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
    return {"message": "Configurações atualizadas", "lateralidade": state.lateralidade}

@app.post("/api/game/reset")
@app.post("/api/session/reset")
def reset_session():
    if state.engine:
        state.engine.reset_session()
        state.engine.reset_rally()
    state.latest_telemetry["stroke_id"] = 3
    state.latest_telemetry["stroke_name"] = "Repouso"
    state.latest_telemetry["confidence"] = 0.0
    state.latest_telemetry["failed_joints"] = []
    state.latest_telemetry["led_active"] = False
    return {"status": "ok", "message": "Sessão reiniciada com sucesso"}

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
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    """
    WebSocket de alta velocidade para streaming de frames da webcam do navegador para a IA do Backend.
    Elimina qualquer incompatibilidade de hardware no Windows e permite feedback instantâneo.
    """
    await websocket.accept()
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
                except Exception:
                    pass

            if raw_bytes and HAS_CV2 and HAS_NUMPY and state.engine:
                nparr = np.frombuffer(raw_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    state.last_client_frame_time = time.time()
                    telemetry = state.engine.process_frame(frame, render_hud=False)
                    state.latest_telemetry = telemetry

                    # Atualiza o buffer JPEG do servidor
                    ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                    if ret:
                        state.latest_jpeg = buffer.tobytes()

                    # Responde com telemetria e coordenadas dos landmarks 3D
                    await websocket.send_text(json.dumps(telemetry))
    except (WebSocketDisconnect, ConnectionResetError, Exception):
        pass

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    state.active_websockets.add(websocket)
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
            except asyncio.TimeoutError:
                pass
    except (WebSocketDisconnect, ConnectionResetError, Exception):
        pass
    finally:
        state.active_websockets.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    print("[TenniSync] Iniciando servidor Web na porta 8000...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
