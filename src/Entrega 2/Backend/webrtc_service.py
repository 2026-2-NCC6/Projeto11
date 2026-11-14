import asyncio
import json
import os
import time
import uuid
from typing import Dict, Optional, Set
import numpy as np
import cv2
import av
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaRelay

try:
    from logger import log_info, log_warn, log_error, log_sampled
except ImportError:
    from Backend.logger import log_info, log_warn, log_error, log_sampled

# Servidores STUN públicos confiáveis
DEFAULT_ICE_SERVERS = [
    RTCIceServer(urls=["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]),
    RTCIceServer(urls=["stun:stun2.l.google.com:19302", "stun:stun.cloudflare.com:3478"])
]

# Servidor TURN configurável via variáveis de ambiente para travessia de CGNAT simétrico rígido
TURN_URL = os.environ.get("TENNISYNC_TURN_URL")
TURN_USER = os.environ.get("TENNISYNC_TURN_USER")
TURN_PASS = os.environ.get("TENNISYNC_TURN_PASS")
if TURN_URL:
    DEFAULT_ICE_SERVERS.append(
        RTCIceServer(urls=[TURN_URL], username=TURN_USER, credential=TURN_PASS)
    )

class WebRTCManager:
    """
    Gerenciador de conexões WebRTC via protocolo UDP para recepção de vídeo e envio de telemetria.
    Opera com 'Latest-Frame Slot' atômico para garantir latência ultra-baixa sem travar o event loop.
    """
    def __init__(self, server_state):
        self.state = server_state
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.active_channels: Dict[str, any] = {}
        self.relay = MediaRelay()

    def get_rtc_configuration(self) -> RTCConfiguration:
        return RTCConfiguration(iceServers=DEFAULT_ICE_SERVERS)

    async def handle_offer(self, offer_dict: dict) -> dict:
        pc_id = str(uuid.uuid4())[:8]
        pc = RTCPeerConnection(configuration=self.get_rtc_configuration())
        self.peer_connections[pc_id] = pc

        log_info("WEBRTC/UDP", f"Nova sessão WebRTC iniciada (ID: {pc_id}) via protocolo UDP.")

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            log_info("WEBRTC/UDP", f"Sessão WebRTC {pc_id} estado da conexão: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                await self._close_peer(pc_id)

        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            log_info("WEBRTC/UDP", f"Sessão WebRTC {pc_id} estado ICE: {pc.iceConnectionState}")
            if pc.iceConnectionState == "failed":
                await self._close_peer(pc_id)

        @pc.on("datachannel")
        def on_datachannel(channel):
            channel_id = f"{pc_id}_{channel.label}"
            self.active_channels[channel_id] = channel
            log_info("WEBRTC/UDP", f"Canal de dados UDP DataChannel conectado: {channel.label} ({channel_id})")

            @channel.on("message")
            def on_message(message):
                if isinstance(message, bytes):
                    # Datagrama UDP com frame JPEG codificado pelo navegador
                    try:
                        nparr = np.frombuffer(message, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            self.state.set_client_frame(frame)
                            # Devolve a telemetria atualizada pelo canal UDP de volta ao cliente
                            if channel.readyState == "open":
                                channel.send(json.dumps(self.state.latest_telemetry))
                    except Exception as e:
                        log_warn("WEBRTC/UDP", f"Erro ao decodificar frame binário via DataChannel: {e}")
                elif isinstance(message, str):
                    try:
                        msg = json.loads(message)
                        if msg.get("type") == "config" and "lateralidade" in msg:
                            self.state.lateralidade = msg["lateralidade"]
                            if self.state.engine:
                                self.state.engine.set_lateralidade(msg["lateralidade"])
                    except Exception:
                        pass

            @channel.on("close")
            def on_close():
                self.active_channels.pop(channel_id, None)

        @pc.on("track")
        def on_track(track):
            if track.kind == "video":
                log_info("WEBRTC/UDP", f"Track de vídeo nativo (SRTP/UDP) conectado na sessão {pc_id}")
                asyncio.ensure_future(self._consume_video_track(track, pc_id))

        offer = RTCSessionDescription(sdp=offer_dict["sdp"], type=offer_dict["type"])
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # Espera reunião inicial de candidatos ICE se necessário
        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
            "session_id": pc_id
        }

    async def _consume_video_track(self, track, pc_id: str):
        """
        Consome continuamente frames do stream de vídeo UDP.
        Deposita o frame no slot atômico do ServerState sem bloquear o event loop.
        """
        frame_count = 0
        try:
            while pc_id in self.peer_connections and track.readyState == "live":
                frame: av.VideoFrame = await track.recv()
                frame_count += 1

                # Converte o frame decodificado do codec de hardware para formato BGR
                img_bgr = frame.to_ndarray(format="bgr24")
                if img_bgr is not None:
                    self.state.set_client_frame(img_bgr)
                    if frame_count % 90 == 0:
                        log_sampled(f"webrtc_video_{pc_id}", 4.0, "WEBRTC/UDP",
                                    f"Streaming UDP ativo. Frame {frame_count} recebido com sucesso ({img_bgr.shape[1]}x{img_bgr.shape[0]}).")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_warn("WEBRTC/UDP", f"Fim do stream de vídeo UDP ({pc_id}): {e}")
        finally:
            log_info("WEBRTC/UDP", f"Receptor de vídeo UDP finalizado para a sessão {pc_id}.")

    async def _close_peer(self, pc_id: str):
        pc = self.peer_connections.pop(pc_id, None)
        if pc:
            try:
                await pc.close()
            except Exception:
                pass
            log_info("WEBRTC/UDP", f"Sessão WebRTC {pc_id} encerrada e recursos liberados.")

    async def close_all(self):
        for pc_id in list(self.peer_connections.keys()):
            await self._close_peer(pc_id)
