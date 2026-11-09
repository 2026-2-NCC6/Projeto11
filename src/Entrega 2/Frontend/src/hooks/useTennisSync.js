import { useState, useEffect, useRef, useCallback } from 'react';
import { createMockStream } from '../services/mockService';
import logger from '../utils/logger';

export function useTennisSync() {
  const [isConnected, setIsConnected] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [sessionActive, setSessionActive] = useState(true);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [lateralidade, setLateralidade] = useState('destro'); // 'destro' ou 'canhoto' (US07)
  const [audioEnabled, setAudioEnabled] = useState(true); // US10 áudio/voz

  // Telemetria em tempo real
  const [telemetry, setTelemetry] = useState({
    fps: 0,
    stroke_id: 3,
    stroke_name: 'Repouso',
    confidence: 0,
    feedback: 'Aguardando inicialização...',
    angles: { elbow_r: 120, elbow_l: 120, knee_r: 160, knee_l: 160, shoulder_r: 90, shoulder_l: 90 },
    failed_joints: [],
    led_active: false,
    active_leds: []
  });

  // Histórico de golpes avaliados
  const [history, setHistory] = useState([]);

  // Referências
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const lastSpokenRef = useRef({ text: '', timestamp: 0 });
  const lastRecordedStrokeRef = useRef({ name: '', timestamp: 0 });
  const lastHandledEventIdRef = useRef(null);
  const sessionActiveRef = useRef(sessionActive);
  sessionActiveRef.current = sessionActive;

  const lateralidadeRef = useRef(lateralidade);
  lateralidadeRef.current = lateralidade;

  // Sintetizador de voz para US10
  const speakFeedback = useCallback((text) => {
    if (!audioEnabled || !window.speechSynthesis || !text) return;
    const now = Date.now();
    // Cooldown de 3.5 segundos para não sobrepor falas
    if (lastSpokenRef.current.text === text && now - lastSpokenRef.current.timestamp < 3500) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'pt-BR';
    utterance.rate = 1.05;
    window.speechSynthesis.speak(utterance);
    lastSpokenRef.current = { text, timestamp: now };
  }, [audioEnabled]);

  // Atualizar histórico quando um novo golpe é classificado
  const handleTelemetryUpdate = useCallback((data) => {
    setTelemetry(data);

    if (sessionActiveRef.current && data.stroke_id >= 0 && data.stroke_id <= 2) {
      if (data.confidence < 0.60) {
        logger.debug('STROKE-REJECT', 'Golpe descartado da telemetria por baixa confiança (< 60%)', {
          stroke: data.stroke_name,
          confidence: data.confidence,
          eventId: data.event_id
        });
        return;
      }

      const eventId = data.event_id;
      const now = Date.now();
      const isNewEvent = (eventId && eventId > 0 && eventId !== lastHandledEventIdRef.current) ||
                         (!eventId && (data.stroke_name !== lastRecordedStrokeRef.current.name || now - lastRecordedStrokeRef.current.timestamp > 3000));

      if (isNewEvent) {
        if (eventId) lastHandledEventIdRef.current = eventId;
        lastRecordedStrokeRef.current = { name: data.stroke_name, timestamp: now };
        
        const isApproved = !data.failed_joints || data.failed_joints.length === 0;

        const newEntry = {
          id: `${now}-${Math.random().toString(36).substr(2, 4)}`,
          timestamp: new Date().toLocaleTimeString('pt-BR'),
          stroke: data.stroke_name,
          confidence: Math.round(data.confidence * 100),
          feedback: data.feedback,
          status: isApproved ? 'approved' : 'correction',
          failed_joints: data.failed_joints || [],
          angles: { ...data.angles }
        };

        setHistory(prev => [newEntry, ...prev.slice(0, 49)]);

        logger.info('STROKE-HIT', `Novo golpe registrado no histórico: ${data.stroke_name}`, {
          stroke: data.stroke_name,
          confidence: `${Math.round(data.confidence * 100)}%`,
          status: isApproved ? 'Aprovado' : 'Correção Necessária',
          falhas: data.failed_joints || []
        });

        // Disparo de voz corretiva se falhou ou de aprovação
        if (data.feedback) {
          speakFeedback(data.feedback);
        }
      }
    }
  }, [speakFeedback]);

  const handleTelemetryUpdateRef = useRef(handleTelemetryUpdate);
  handleTelemetryUpdateRef.current = handleTelemetryUpdate;

  // Conexão WebSocket estável com o Backend (não reinicia com atualizações de telemetria)
  useEffect(() => {
    let unmounted = false;
    let mockCleanup = null;

    const connectWebSocket = () => {
      if (unmounted) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname || 'localhost';
      const wsUrl = `${protocol}//${host}:8000/ws/telemetry`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (unmounted) return;
          logger.info('WEBSOCKET', 'Canal de telemetria conectado (/ws/telemetry)');
          setIsConnected(true);
          setIsDemoMode(false);
          if (mockCleanup) {
            mockCleanup();
            mockCleanup = null;
          }
          // Envia configuração inicial
          ws.send(JSON.stringify({ type: 'config', lateralidade: lateralidadeRef.current }));
        };

        ws.onmessage = (event) => {
          if (unmounted) return;
          try {
            const data = JSON.parse(event.data);
            handleTelemetryUpdateRef.current(data);
          } catch (e) {
            logger.error('WEBSOCKET', 'Falha ao decodificar JSON da telemetria', { error: e?.message });
          }
        };

        ws.onclose = () => {
          if (unmounted) return;
          logger.warn('WEBSOCKET', 'Canal de telemetria fechado. Ativando fallback de simulação e agendando reconexão...');
          setIsConnected(false);
          setIsDemoMode(true);
          if (!mockCleanup) {
            mockCleanup = createMockStream((d) => handleTelemetryUpdateRef.current(d));
          }
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 4000);
        };

        ws.onerror = (err) => {
          logger.error('WEBSOCKET', 'Erro na conexão WebSocket de telemetria', err);
          ws.close();
        };
      } catch (err) {
        logger.error('WEBSOCKET', 'Falha ao inicializar WebSocket de telemetria', err);
        setIsDemoMode(true);
        if (!mockCleanup) {
          mockCleanup = createMockStream((d) => handleTelemetryUpdateRef.current(d));
        }
      }
    };

    connectWebSocket();

    return () => {
      unmounted = true;
      if (wsRef.current) {
        wsRef.current.onclose = null; // evita loop no unmount
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (mockCleanup) mockCleanup();
    };
  }, []); // Sem dependências que recriem o socket a cada render!

  // Timer da sessão
  useEffect(() => {
    let interval = null;
    if (sessionActive) {
      interval = setInterval(() => {
        setSessionSeconds(prev => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [sessionActive]);

  // Estatísticas calculadas
  const stats = {
    total: history.length,
    approved: history.filter(h => h.status === 'approved').length,
    corrections: history.filter(h => h.status === 'correction').length,
    accuracy: history.length > 0 
      ? Math.round((history.filter(h => h.status === 'approved').length / history.length) * 100) 
      : 100,
    forehands: history.filter(h => h.stroke === 'Forehand').length,
    backhands: history.filter(h => h.stroke === 'Backhand').length,
    saques: history.filter(h => h.stroke === 'Saque').length
  };

  const toggleSession = () => setSessionActive(prev => !prev);
  const resetSession = () => {
    setSessionSeconds(0);
    setHistory([]);
    logger.info('SYSTEM', 'Sessão reiniciada pelo usuário');
    logger.fetchWithLog('/api/session/reset', { method: 'POST' }, 'API-HTTP');
  };

  const toggleHandedness = () => {
    const next = lateralidade === 'destro' ? 'canhoto' : 'destro';
    setLateralidade(next);
    logger.info('SYSTEM', `Lateralidade alterada para: ${next}`);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'config', lateralidade: next }));
    }
  };

  const toggleAudio = () => setAudioEnabled(prev => !prev);

  const resetRallyGame = () => {
    logger.info('SYSTEM', 'Partida reiniciada pelo usuário');
    logger.fetchWithLog('/api/game/reset', { method: 'POST' }, 'API-HTTP');
  };

  return {
    isConnected,
    isDemoMode,
    sessionActive,
    sessionSeconds,
    lateralidade,
    audioEnabled,
    telemetry,
    latestReplayUrl: telemetry.latest_replay_url,
    gameState: telemetry.game,
    history,
    stats,
    handleTelemetryUpdate,
    toggleSession,
    resetSession,
    toggleHandedness,
    toggleAudio,
    resetRallyGame
  };
}
