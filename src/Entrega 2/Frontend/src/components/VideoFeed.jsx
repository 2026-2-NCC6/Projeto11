import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Camera, Zap, AlertCircle, Moon, UserCheck, UserX, RefreshCw, Radio, Wifi } from 'lucide-react';
import { TennisGameCourtOverlay } from './TennisGameCourtOverlay';
import logger from '../utils/logger';
import authClient from '../utils/authClient';

// Conexões anatômicas padrão do MediaPipe Pose
const POSE_CONNECTIONS = [
  // Tronco
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Braço Esquerdo (ombro 11 -> cotovelo 13 -> pulso 15)
  [11, 13], [13, 15],
  // Braço Direito (ombro 12 -> cotovelo 14 -> pulso 16)
  [12, 14], [14, 16],
  // Perna Esquerda (quadril 23 -> joelho 25 -> tornozelo 27)
  [23, 25], [25, 27],
  // Perna Direita (quadril 24 -> joelho 26 -> tornozelo 28)
  [24, 26], [26, 28]
];

export function VideoFeed({
  isConnected,
  isDemoMode,
  fps,
  currentStroke,
  feedback,
  failedJoints,
  athleteDetected,
  isDark,
  telemetry,
  onTelemetryUpdate,
  gameState,
  onResetGame,
  containerHeight = '460px'
}) {
  const [useLocalCamera, setUseLocalCamera] = useState(true);
  const [cameraReady, setCameraReady] = useState(false);
  const [transportProtocol, setTransportProtocol] = useState('Iniciando...');
  const [streamError, setStreamError] = useState(null);
  const [streamKey, setStreamKey] = useState(Date.now());

  // Atualiza a chave do stream quando a conexão é restabelecida
  useEffect(() => {
    if (isConnected) {
      setStreamKey(Date.now());
    }
  }, [isConnected]);

  const videoRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const offscreenCanvasRef = useRef(null);
  const wsVideoRef = useRef(null);
  const streamRef = useRef(null);
  const isSendingFrameRef = useRef(false);
  const animationFrameRef = useRef(null);

  // Função para desenhar esqueleto e articulações sobre o vídeo
  const renderSkeletonOverlay = useCallback((landmarks, failed = []) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    if (!landmarks || landmarks.length < 25) return;

    // 1. Linhas dos ossos/segmentos anatômicos
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#10b981'; // Verde esmeralda brilhante

    for (const [i, j] of POSE_CONNECTIONS) {
      const p1 = landmarks[i];
      const p2 = landmarks[j];
      if (p1 && p2 && (p1[2] ?? 1) > 0.35 && (p2[2] ?? 1) > 0.35) {
        ctx.beginPath();
        ctx.moveTo(p1[0] * width, p1[1] * height);
        ctx.lineTo(p2[0] * width, p2[1] * height);
        ctx.stroke();
      }
    }

    // 2. Pontos das articulações corporais (índices 11 a 28)
    for (let idx = 11; idx <= 28; idx++) {
      const p = landmarks[idx];
      if (!p || (p[2] ?? 1) <= 0.35) continue;

      const isFailed = (failed.includes('cotovelo_dir') && idx === 14) ||
                       (failed.includes('cotovelo_esq') && idx === 13) ||
                       (failed.includes('joelho_dir') && idx === 26) ||
                       (failed.includes('joelho_esq') && idx === 25) ||
                       (failed.includes('ombro_dir') && idx === 12) ||
                       (failed.includes('ombro_esq') && idx === 11);

      ctx.beginPath();
      ctx.arc(p[0] * width, p[1] * height, isFailed ? 7 : 5, 0, 2 * Math.PI);
      ctx.fillStyle = isFailed ? '#ef4444' : '#34d399';
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();
    }
  }, []);

  // Limpa o overlay quando não há atleta
  const clearSkeletonOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  // Efeito principal: Gerenciamento da Webcam e Streaming via protocolo UDP (WebRTC) com Fallback WSS
  useEffect(() => {
    let unmounted = false;
    let stream = null;
    let pc = null;
    let dc = null;
    let ws = null;
    let frameInterval = null;
    let rtcTimeout = null;

    if (!useLocalCamera) {
      setCameraReady(false);
      clearSkeletonOverlay();
      return;
    }

    // Inicializa offscreen canvas se necessário
    if (!offscreenCanvasRef.current) {
      const off = document.createElement('canvas');
      off.width = 640;
      off.height = 480;
      offscreenCanvasRef.current = off;
    }

    const startWebSocketFallback = () => {
      if (unmounted || ws) return;
      setTransportProtocol('WSS (Fallback)');
      const wsVideoUrl = authClient.getWsUrl('/ws/video');
      logger.info('WEBSOCKET', 'Iniciando canal WebSocket de vídeo como fallback:', wsVideoUrl);

      try {
        ws = new WebSocket(wsVideoUrl);
        ws.onopen = () => {
          if (unmounted) return;
          logger.info('WEBSOCKET', 'Canal WebSocket de vídeo (/ws/video) pronto.');
        };

        ws.onmessage = (event) => {
          if (unmounted) return;
          isSendingFrameRef.current = false;
          try {
            const telemetryData = JSON.parse(event.data);
            if (onTelemetryUpdate) onTelemetryUpdate(telemetryData);
            if (telemetryData.landmarks) {
              renderSkeletonOverlay(telemetryData.landmarks, telemetryData.failed_joints || []);
            } else {
              clearSkeletonOverlay();
            }
          } catch (e) {
            logger.error('WEBSOCKET', 'Erro ao processar telemetria recebida:', e);
          }
        };

        ws.onerror = (e) => {
          logger.warn('WEBSOCKET', 'Erro no canal WebSocket de vídeo:', e);
          isSendingFrameRef.current = false;
        };

        ws.onclose = () => {
          isSendingFrameRef.current = false;
        };
      } catch (e) {
        logger.error('WEBSOCKET', 'Falha ao instanciar WebSocket /ws/video:', e);
      }
    };

    // Abre a câmera do navegador via getUserMedia
    navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        frameRate: { ideal: 30, max: 30 }
      },
      audio: false
    })
      .then(async (s) => {
        if (unmounted) {
          s.getTracks().forEach(t => t.stop());
          return;
        }
        stream = s;
        streamRef.current = s;

        if (videoRef.current) {
          videoRef.current.srcObject = s;
          videoRef.current.onloadedmetadata = () => {
            if (unmounted) return;
            videoRef.current.play().catch(() => {});
            setCameraReady(true);
            setStreamError(null);

            // Preservação de proporção anatômica (Aspect Ratio)
            const vw = videoRef.current.videoWidth || 640;
            const vh = videoRef.current.videoHeight || 480;
            if (overlayCanvasRef.current) {
              overlayCanvasRef.current.width = vw;
              overlayCanvasRef.current.height = vh;
            }
            if (offscreenCanvasRef.current) {
              let targetW = 640;
              let targetH = Math.round((vh / vw) * 640);
              if (vh > vw) {
                targetH = 640;
                targetW = Math.round((vw / vh) * 640);
              }
              offscreenCanvasRef.current.width = targetW;
              offscreenCanvasRef.current.height = targetH;
            }

            logger.info('CAM/STREAM', `Webcam iniciada: ${vw}x${vh} @ 30 FPS.`);
          };
        }

        // ==============================================================================
        // INICIA SESSÃO WEBRTC VIA PROTOCOLO UDP
        // ==============================================================================
        try {
          setTransportProtocol('Negociando UDP...');
          const iceRes = await authClient.fetchWithAuth('/api/webrtc/ice_servers').catch(() => null);
          const iceData = iceRes && iceRes.ok ? await iceRes.json().catch(() => null) : null;
          const rtcConfig = iceData || {
            iceServers: [
              { urls: ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302'] },
              { urls: ['stun:stun2.l.google.com:19302', 'stun:stun.cloudflare.com:3478'] }
            ]
          };

          pc = new RTCPeerConnection(rtcConfig);

          // Adiciona o track de vídeo para streaming UDP nativo (SRTP)
          s.getTracks().forEach(track => pc.addTrack(track, s));

          // Cria canal de dados UDP sem retransmissão para baixa latência
          dc = pc.createDataChannel('udp-telemetry', { ordered: false, maxRetransmits: 0 });
          dc.onopen = () => {
            if (unmounted) return;
            setTransportProtocol('UDP (WebRTC)');
            logger.info('WEBRTC/UDP', 'Canal de dados UDP DataChannel pronto.');
          };

          dc.onmessage = (event) => {
            if (unmounted) return;
            isSendingFrameRef.current = false;
            try {
              const telemetryData = JSON.parse(event.data);
              if (onTelemetryUpdate) onTelemetryUpdate(telemetryData);
              if (telemetryData.landmarks) {
                renderSkeletonOverlay(telemetryData.landmarks, telemetryData.failed_joints || []);
              } else {
                clearSkeletonOverlay();
              }
            } catch (e) {
              logger.error('WEBRTC/UDP', 'Erro ao decodificar telemetria UDP:', e);
            }
          };

          pc.oniceconnectionstatechange = () => {
            if (unmounted) return;
            logger.info('WEBRTC/UDP', `Estado ICE WebRTC: ${pc.iceConnectionState}`);
            if (['connected', 'completed'].includes(pc.iceConnectionState)) {
              setTransportProtocol('UDP (WebRTC)');
            } else if (pc.iceConnectionState === 'failed') {
              startWebSocketFallback();
            }
          };

          const offer = await pc.createOffer();
          await pc.setLocalDescription(offer);

          // Aguarda reunião inicial de candidatos STUN
          await new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
              resolve();
            } else {
              const checkState = () => {
                if (pc.iceGatheringState === 'complete') {
                  pc.removeEventListener('icegatheringstatechange', checkState);
                  resolve();
                }
              };
              pc.addEventListener('icegatheringstatechange', checkState);
              setTimeout(resolve, 800);
            }
          });

          const offerRes = await authClient.fetchWithAuth('/api/webrtc/offer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type })
          });

          if (!offerRes.ok) throw new Error('Servidor recusou oferta SDP');
          const answer = await offerRes.json();
          await pc.setRemoteDescription(new RTCSessionDescription(answer));
          setTransportProtocol('UDP (WebRTC)');
          logger.info('WEBRTC/UDP', 'Sessão WebRTC UDP estabelecida com sucesso.');
        } catch (err) {
          logger.warn('WEBRTC/UDP', 'WebRTC UDP bloqueado ou indisponível. Ativando fallback WebSocket:', err);
          startWebSocketFallback();
        }

        // Watchdog de 4.5s para fallback automático
        rtcTimeout = setTimeout(() => {
          if (!unmounted && (!pc || !['connected', 'completed'].includes(pc.iceConnectionState))) {
            logger.warn('WEBRTC/UDP', 'Timeout na negociação ICE UDP. Chaveando para fallback.');
            startWebSocketFallback();
          }
        }, 4500);

        // Loop contínuo de captura e envio de frames a ~25 FPS
        frameInterval = setInterval(() => {
          if (unmounted) return;
          const video = videoRef.current;
          const offscreen = offscreenCanvasRef.current;
          const isDcOpen = dc && dc.readyState === 'open';
          const isWsOpen = ws && ws.readyState === WebSocket.OPEN;

          if (video && video.readyState >= 2 && offscreen && (isDcOpen || isWsOpen) && !isSendingFrameRef.current) {
            isSendingFrameRef.current = true;
            const ctx = offscreen.getContext('2d');
            ctx.drawImage(video, 0, 0, offscreen.width, offscreen.height);

            offscreen.toBlob((blob) => {
              if (unmounted) return;
              if (blob) {
                if (isDcOpen) {
                  blob.arrayBuffer().then(buf => {
                    if (dc.readyState === 'open') dc.send(buf);
                    else isSendingFrameRef.current = false;
                  }).catch(() => { isSendingFrameRef.current = false; });
                } else if (isWsOpen) {
                  ws.send(blob);
                } else {
                  isSendingFrameRef.current = false;
                }
              } else {
                isSendingFrameRef.current = false;
              }
            }, 'image/jpeg', 0.65);
          }
        }, 40); // 25 FPS
      })
      .catch((err) => {
        if (unmounted) return;
        logger.error('CAM/STREAM', 'Câmera local indisponível no navegador:', err);
        setStreamError('Câmera indisponível no navegador. Verifique permissões.');
      });

    return () => {
      unmounted = true;
      if (rtcTimeout) clearTimeout(rtcTimeout);
      if (frameInterval) clearInterval(frameInterval);
      if (stream) {
        stream.getTracks().forEach(t => t.stop());
      }
      if (dc) {
        try { dc.close(); } catch (e) {}
      }
      if (pc) {
        try { pc.close(); } catch (e) {}
      }
      if (ws) {
        try { ws.close(); } catch (e) {}
      }
      clearSkeletonOverlay();
    };
  }, [useLocalCamera, renderSkeletonOverlay, clearSkeletonOverlay, onTelemetryUpdate]);

  return (
    <div className="glass-panel" style={{ overflow: 'hidden', position: 'relative', display: 'flex', flexDirection: 'column' }}>
      
      {/* Barra Superior do Feed de Vídeo */}
      <div style={{
        padding: '12px 18px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(15, 23, 42, 0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Camera size={18} color="#10b981" />
          <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>Feed Visual do Atleta</span>
          
          {/* Status de Presença do Atleta */}
          {isConnected && (
            <span
              className={`badge ${athleteDetected ? 'badge-emerald' : 'badge-slate'}`}
              style={{ fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              {athleteDetected ? <UserCheck size={11} /> : <UserX size={11} />}
              {athleteDetected ? 'Atleta em Campo' : 'Aguardando Atleta'}
            </span>
          )}

          {isDark && (
            <span className="badge badge-amber" style={{ fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Moon size={11} /> Pouca Luz
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Alternador de Modo de Câmera */}
          <button
            onClick={() => setUseLocalCamera(prev => !prev)}
            className={`btn ${useLocalCamera ? 'btn-primary' : 'btn-secondary'}`}
            style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '5px' }}
            title={useLocalCamera ? 'Clique para usar Câmera do Servidor (OpenCV)' : 'Clique para usar Câmera do Navegador'}
          >
            <Camera size={13} />
            <span>{useLocalCamera ? '📹 Câmera Navegador (Ativa)' : '🖥️ Câmera OpenCV'}</span>
          </button>

          {/* Badge de Protocolo de Transporte */}
          <div style={{
            background: transportProtocol.includes('UDP') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(14, 165, 233, 0.15)',
            border: `1px solid ${transportProtocol.includes('UDP') ? '#10b981' : '#38bdf8'}`,
            padding: '3px 8px',
            borderRadius: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.72rem',
            color: transportProtocol.includes('UDP') ? '#34d399' : '#38bdf8',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <Radio size={12} color={transportProtocol.includes('UDP') ? '#10b981' : '#38bdf8'} />
            <span>{transportProtocol}</span>
          </div>

          {/* Badge de FPS */}
          <div style={{
            background: 'rgba(0,0,0,0.4)',
            padding: '3px 8px',
            borderRadius: '6px',
            border: '1px solid rgba(255,255,255,0.1)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            color: '#34d399',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <Zap size={12} color="#10b981" />
            <span>{fps || 30} FPS</span>
          </div>
        </div>
      </div>

      {/* Área de Visualização Principal */}
      <div style={{ position: 'relative', width: '100%', height: containerHeight, background: '#020617', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        
        {/* Modo 1: Câmera Local do Navegador com Canvas de Esqueleto sobreposto */}
        {useLocalCamera ? (
          <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
            {/* Canvas de Sobreposição MediaPipe com Esqueleto e Articulações */}
            <canvas
              ref={overlayCanvasRef}
              width={640}
              height={480}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                pointerEvents: 'none'
              }}
            />
          </div>
        ) : isConnected ? (
          /* Modo 2: Stream MJPEG do Backend com Landmarks MediaPipe */
          <img
            key={streamKey}
            src={`/api/video_feed?t=${streamKey}`}
            alt="Feed ao vivo TenniSync OpenCV"
            style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
            onError={() => {
              // Tenta reconectar o stream automaticamente após 1.5s
              setTimeout(() => setStreamKey(Date.now()), 1500);
            }}
          />
        ) : (
          /* Estado offline limpo (sem simulação falsa) */
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            padding: '24px',
            textAlign: 'center'
          }}>
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: '50%',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <AlertCircle size={32} color="#ef4444" />
            </div>
            <h4 style={{ margin: 0, fontSize: '1rem', color: '#f8fafc', fontWeight: '600' }}>
              Servidor Backend Desconectado
            </h4>
            <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', maxWidth: '360px' }}>
              Inicie o backend em Python para transmitir a IA e visão computacional em tempo real:
            </p>
            <code style={{
              background: 'rgba(0,0,0,0.6)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '0.78rem',
              color: '#34d399',
              border: '1px solid rgba(255,255,255,0.1)'
            }}>
              py -3.11 server.py
            </code>
          </div>
        )}

        {/* Camada de Gamificacao do Jogo Virtual (Quadra, Sombra, Bola 3D, Timing e Multiplayer 2 Jogadores) */}
        <TennisGameCourtOverlay
          telemetry={telemetry}
          athleteDetected={athleteDetected}
          ballChallenge={gameState?.ball_challenge || telemetry?.game?.ball_challenge}
          lives={gameState?.lives ?? telemetry?.game?.lives ?? 3}
          maxLives={gameState?.max_lives ?? telemetry?.game?.max_lives ?? 3}
          score={gameState?.score ?? telemetry?.game?.score ?? 0}
          comboStreak={gameState?.combo_streak ?? telemetry?.game?.combo_streak ?? 0}
          comboMultiplier={gameState?.combo_multiplier ?? telemetry?.game?.combo_multiplier ?? 1.0}
          rallyCount={gameState?.rally_count ?? telemetry?.game?.rally_count ?? 0}
          bestRally={gameState?.best_rally ?? telemetry?.game?.best_rally ?? 0}
          isGameOver={gameState?.is_game_over ?? telemetry?.game?.is_game_over ?? false}
          lastFeedback={gameState?.last_feedback ?? telemetry?.game?.last_feedback ?? ''}
          lastGrade={gameState?.last_grade ?? telemetry?.game?.last_grade ?? 'NONE'}
          onResetGame={onResetGame}
        />

        {/* HUD Overlay em tempo real sobre o vídeo */}
        <div style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          pointerEvents: 'none'
        }}>
          {/* Tag de Golpe Detectado com Persistência */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.88)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '8px',
            padding: '6px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)'
          }}>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Golpe:
            </span>
            <span style={{
              fontWeight: '700',
              fontSize: '1rem',
              color: currentStroke === 'Repouso' ? '#94a3b8' : '#34d399'
            }}>
              {currentStroke}
            </span>
          </div>

          {/* Notificação HUD de Biomecânica */}
          {feedback && (
            <div style={{
              background: failedJoints && failedJoints.length > 0 
                ? 'rgba(239, 68, 68, 0.92)' 
                : currentStroke === 'Repouso'
                  ? 'rgba(30, 41, 59, 0.85)'
                  : 'rgba(16, 185, 129, 0.92)',
              color: '#ffffff',
              padding: '7px 14px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: '600',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              maxWidth: '420px',
              backdropFilter: 'blur(6px)',
              border: '1px solid rgba(255,255,255,0.1)'
            }}>
              {feedback}
            </div>
          )}
        </div>

        {/* Informações de diagnóstico no rodapé do player */}
        <div style={{
          position: 'absolute',
          bottom: '12px',
          right: '16px',
          left: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          pointerEvents: 'none'
        }}>
          <div style={{
            background: 'rgba(15, 23, 42, 0.85)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.7rem',
            color: '#cbd5e1'
          }}>
            MediaPipe Pose 3D + TennisTransformerGPU (99.4% Acc)
          </div>
          <div style={{
            background: 'rgba(15, 23, 42, 0.85)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '0.7rem',
            color: isConnected ? '#34d399' : '#ef4444'
          }}>
            ● {isConnected ? 'Pipeline Ativo em Tempo Real' : 'Aguardando Servidor'}
          </div>
        </div>

      </div>
    </div>
  );
}
