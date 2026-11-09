import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Heart, Flame, AlertCircle, Users, Bot, Gauge, Sparkles, Layers, MousePointer, Ruler, Zap } from 'lucide-react';
import { playHitSound, playServeSound, playBounceSound, playFaultSound, playComboSound } from '../utils/tennisAudio';
import {
  ROOM, DEFAULT_CALIBRATION, project3DTo2D, mouseToAim, describeDepth, calibrateRoomFromPose,
  estimateAthlete3D, createShot, sampleShot, createReturn, sampleReturn, clamp
} from '../utils/tennis3DPhysics';
import logger from '../utils/logger';

const HIT_Z_TOLERANCE = 0.70;  // janela de rebatida em torno da profundidade do atleta (m)
const HIT_REACH = 1.30;        // alcance lateral da raquete (m)
const START_HUD_BOT = { text: '🤖 Modo Robô Ativo: a IA dita e sorteia aleatoriamente os cantos da quadra!', color: '#c084fc' };
const START_HUD_PVP = { text: '🖱️ Jogador do Mouse: escolha lado e profundidade e clique para lançar!', color: '#38bdf8' };

export function TennisGameCourtOverlay({
  telemetry = {},
  athleteDetected = false,
  lives: externalLives = 3,
  maxLives = 3,
  score: externalScore = 0,
  comboStreak: externalCombo = 0,
  comboMultiplier: externalMultiplier = 1.0,
  rallyCount: externalRally = 0,
  isGameOver: externalGameOver = false,
  onResetGame
}) {
  const canvasRef = useRef(null);
  const animFrameIdRef = useRef(null);
  const pendingGameOverRef = useRef(false);

  // 'bot' (IA sorteia cantos aleatoriamente) ou 'multiplayer' (segundo jogador no mouse)
  const [gameMode, setGameMode] = useState('bot');
  const [courtMode, setCourtMode] = useState('floor');
  const [speedLevel, setSpeedLevel] = useState(2);
  const [calibState, setCalibState] = useState('PROMPT'); // PROMPT | READY
  const [calibMsg, setCalibMsg] = useState('');
  const [hudStatus, setHudStatus] = useState(START_HUD_BOT);

  const [localLives, setLocalLives] = useState(maxLives);
  const [localScore, setLocalScore] = useState(externalScore);
  const [localComboStreak, setLocalComboStreak] = useState(externalCombo);
  const [localComboMultiplier, setLocalComboMultiplier] = useState(externalMultiplier);
  const [localRallyCount, setLocalRallyCount] = useState(externalRally);
  const [isGameOverLocal, setIsGameOverLocal] = useState(externalGameOver);

  const calibRef = useRef({ ...DEFAULT_CALIBRATION });
  const calibStateRef = useRef('PROMPT');
  const telemetryRef = useRef(telemetry);
  const athleteRef = useRef({ x: 0, z: 2.7, wristX: 0, swing: 0 });
  const mousePosRef = useRef({ x: 0.5, y: 0.6, isInside: false });
  const lastProcessedEventIdRef = useRef(null);
  const bounceRingsRef = useRef([]);

  // Estados e controle autônomo do Robô
  const gameModeRef = useRef('bot');
  const botAimRef = useRef({ x: 0.85, z: 2.1, inBounds: true });
  const botNextLaunchTimeRef = useRef(0);
  const botLaunchedRef = useRef(false);
  const botPrepareDurationRef = useRef(1700);

  // Estados de presença do Atleta e Contagem Obrigatória de 8 segundos
  // 'WAITING_ATHLETE' | 'COUNTDOWN_8S' | 'READY' | 'PAUSED_NO_ATHLETE'
  const [presenceState, setPresenceState] = useState(athleteDetected ? 'COUNTDOWN_8S' : 'WAITING_ATHLETE');
  const [countdownRemaining, setCountdownRemaining] = useState(8);
  const countdownStartRef = useRef(athleteDetected ? Date.now() : null);
  const athleteDetectedRef = useRef(athleteDetected);
  const presenceStateRef = useRef(presenceState);

  const getFlightDuration = useCallback((level = speedLevel) => {
    switch (Number(level)) {
      case 1: return 3.4;
      case 2: return 2.8;
      case 3: return 2.2;
      case 4: return 1.6;
      default: return 2.8;
    }
  }, [speedLevel]);

  /**
   * Estados: BALL_WITH_MOUSE -> BALL_TO_ATHLETE (rede -> quique -> sobe ao atleta -> cai no fundo se errar)
   *          -> BALL_TO_MOUSE (rebatida no ar, devolução angular) | FAULT_RESULT
   */
  const gameStateRef = useRef({
    status: 'BALL_WITH_MOUSE',
    shot: null,
    ret: null,
    flightDuration: 2.8,
    startTime: Date.now(),
    progress: 0,
    lastEventTime: Date.now(),
    particles: [],
    shakeFrames: 0,
    bouncedMid: false,
    bouncedBack: false,
    missed: false
  });

  const deductLife = useCallback((reason = 'BALL_MISSED', detailText = '') => {
    playFaultSound();
    setLocalLives(prev => {
      const next = Math.max(0, prev - 1);
      logger.warn('GAME-MISS', 'Vida descontada do jogador!', {
        motivo: reason,
        vidasAntes: prev,
        vidasDepois: next,
        statusJogo: gameStateRef.current.status
      });
      if (next <= 0) {
        pendingGameOverRef.current = true;
        logger.warn('GAME-MISS', 'Última vida perdida! Game Over será acionado após a bola concluir a trajetória e tocar o chão do fundo.');
      }
      return next;
    });
    setLocalComboStreak(0);
    setLocalComboMultiplier(1.0);
    const msg = detailText || '❌ BOLA PERDIDA! A bola cruzou o atleta e caiu no chão (-1 Vida)';
    setHudStatus({ text: msg, color: '#ef4444' });
    logger.fetchWithLog('/api/game/miss', { method: 'POST' }, 'API-HTTP');
  }, []);

  // Calibração guiada: atleta encostado na parede do fundo (Z = 3,5 m)
  const calibrateNow = useCallback(() => {
    const canvas = canvasRef.current;
    const c = calibrateRoomFromPose(telemetryRef.current?.landmarks, canvas?.width || 800, canvas?.height || 600);
    if (!c) {
      setCalibMsg('Não foi possível ler o corpo inteiro. Afaste-se, encoste na parede do fundo e mostre cabeça e pés.');
      return;
    }
    calibRef.current = c;
    setCalibMsg('');
    setCalibState('READY');
    setHudStatus({
      text: gameModeRef.current === 'bot'
        ? '📐 Sala calibrada (3,5m)! O Robô iniciará os lançamentos aleatórios.'
        : '📐 Sala calibrada (3,5m)! Lance a bola com o mouse.',
      color: '#4ade80'
    });
    if (gameModeRef.current === 'bot') {
      botNextLaunchTimeRef.current = Date.now() + 1500;
      botLaunchedRef.current = false;
    }
  }, []);

  const useDefaultRoom = useCallback(() => {
    calibRef.current = { ...DEFAULT_CALIBRATION };
    setCalibMsg('');
    setCalibState('READY');
    setHudStatus({
      text: gameModeRef.current === 'bot'
        ? '📐 Usando sala padrão (3,5m x 3,5m)! Robô pronto para ditar o jogo.'
        : '📐 Usando sala padrão de 3,5m x 3,5m.',
      color: '#facc15'
    });
    if (gameModeRef.current === 'bot') {
      botNextLaunchTimeRef.current = Date.now() + 1500;
      botLaunchedRef.current = false;
    }
  }, []);

  // Inteligência Artificial do Robô: dita e sorteia aleatoriamente os cantos e profundidades da quadra
  const generateRandomBotAim = useCallback(() => {
    const athlete = athleteRef.current;
    // 1. Lado estocástico: 45% direita, 45% esquerda, 10% centro
    const sideRoll = Math.random();
    let x;
    if (sideRoll < 0.45) {
      x = 0.55 + Math.random() * 0.85; // lado direito (+0.55m a +1.40m)
    } else if (sideRoll < 0.90) {
      x = -0.55 - Math.random() * 0.85; // lado esquerdo (-0.55m a -1.40m)
    } else {
      x = (Math.random() - 0.5) * 0.7; // centro (-0.35m a +0.35m)
    }

    // 2. Profundidade estocástica: curta (30%), média (45%), fundo (25%)
    const depthRoll = Math.random();
    let z;
    if (depthRoll < 0.30) {
      z = 1.25 + Math.random() * 0.5; // curta (1.25m - 1.75m)
    } else if (depthRoll < 0.75) {
      z = 1.8 + Math.random() * 0.55; // média (1.8m - 2.35m)
    } else {
      const maxZ = Math.max(1.9, athlete.z - 0.45);
      z = 2.4 + Math.random() * Math.max(0.15, maxZ - 2.4); // fundo
    }

    x = clamp(x, -ROOM.halfWidth * 0.90, ROOM.halfWidth * 0.90);
    z = clamp(z, ROOM.zNet + 0.35, ROOM.zBackLine - 0.15);

    return { x, z, inBounds: true };
  }, []);

  // Agendamento de lançamento autônomo do Robô
  // Agendamento de lançamento autônomo do Robô
  const scheduleBotLaunch = useCallback((delayOverride = null) => {
    const nextAim = generateRandomBotAim();
    botAimRef.current = nextAim;
    botLaunchedRef.current = false;
    const baseDelay = delayOverride !== null ? delayOverride : (
      speedLevel === 4 ? 750 : (speedLevel === 3 ? 1200 : (speedLevel === 2 ? 1700 : 2300))
    );
    botPrepareDurationRef.current = baseDelay;
    botNextLaunchTimeRef.current = Date.now() + baseDelay;
    const sideText = nextAim.x > 0.3 ? 'DIREITO' : (nextAim.x < -0.3 ? 'ESQUERDO' : 'CENTRAL');
    logger.info('BOT-AI', 'Robô sorteou novo alvo estocástico e agendou arremesso', {
      lado: sideText,
      alvoX: Number(nextAim.x.toFixed(2)),
      alvoZ: Number(nextAim.z.toFixed(2)),
      profundidade: describeDepth(nextAim.z),
      delayMs: baseDelay
    });
    setHudStatus({
      text: `🤖 Robô sorteou: LADO ${sideText} (${describeDepth(nextAim.z)})! Lançando...`,
      color: '#c084fc'
    });
  }, [generateRandomBotAim, speedLevel]);

  // 1. LANÇAMENTO DA BOLA (Pelo Robô ou pelo Jogador do Mouse)
  const launchBall = useCallback((aim, originX = null) => {
    const gs = gameStateRef.current;
    if (isGameOverLocal || calibStateRef.current !== 'READY') return;

    // TRAVA OBRIGATÓRIA: Nenhuma bola pode ser arremessada antes de completar os 8 segundos de preparação!
    if (presenceStateRef.current !== 'READY') {
      playFaultSound();
      logger.warn('BALL-3D', 'Lançamento de bola bloqueado: atleta ainda não está pronto', {
        presenceState: presenceStateRef.current,
        countdownRemaining
      });
      setHudStatus({
        text: presenceStateRef.current === 'COUNTDOWN_8S'
          ? `⏳ Aguarde o tempo de preparação (${countdownRemaining}s) para arremessar!`
          : '👤 Aguardando o atleta entrar na frente da câmera!',
        color: '#f97316'
      });
      return;
    }

    if (!aim.inBounds) {
      playFaultSound();
      gs.shakeFrames = 6;
      logger.warn('BALL-3D', 'Tentativa de arremesso OUT (fora das linhas da quadra)', { aim });
      setHudStatus({ text: `🚨 OUT! (${describeDepth(aim.z)}) Mire dentro das linhas da quadra.`, color: '#f97316' });
      return;
    }
    const athlete = athleteRef.current;
    const z1 = Math.min(aim.z, athlete.z - 0.45);
    const startX = originX !== null ? originX : clamp(mousePosRef.current.x - 0.5, -0.5, 0.5) * 2 * ROOM.halfWidth * 0.6;
    gs.shot = createShot(startX, aim.x, z1);
    gs.status = 'BALL_TO_ATHLETE';
    gs.startTime = Date.now();
    gs.flightDuration = getFlightDuration();
    gs.progress = 0;
    gs.bouncedMid = false;
    gs.bouncedBack = false;
    gs.missed = false;
    playServeSound();
    const side = aim.x > 0.3 ? 'DIREITO' : (aim.x < -0.3 ? 'ESQUERDO' : 'CENTRAL');
    const source = gameModeRef.current === 'bot' ? '🤖 Robô lançou' : '🎾 Bola';

    logger.info('BALL-3D', 'Bola lançada em direção ao atleta', {
      modo: gameModeRef.current,
      origemX: Number(startX.toFixed(2)),
      alvoX: Number(aim.x.toFixed(2)),
      quiqueZ: Number(z1.toFixed(2)),
      duracaoVoo: Number(gs.flightDuration.toFixed(2)),
      lado: side
    });

    setHudStatus({ text: `${source} ${describeDepth(z1)} no lado ${side}!`, color: '#facc15' });
  }, [isGameOverLocal, getFlightDuration, countdownRemaining]);

  // 2. ATLETA REBATE NO AR -> devolução angular ao mouse
  const returnBallToMouse = useCallback((strokeName, qualityScore = 1.0) => {
    const gs = gameStateRef.current;
    const canvas = canvasRef.current;
    const w = canvas ? canvas.width : 800;
    const h = canvas ? canvas.height : 600;
    const ball = sampleShot(gs.shot, gs.progress);
    const athlete = athleteRef.current;

    playHitSound();
    const pt = project3DTo2D(ball.x, ball.y, ball.z, calibRef.current, w, h);
    const parts = [];
    for (let i = 0; i < 26; i++) {
      const angle = Math.random() * Math.PI * 2;
      const spd = 3 + Math.random() * 6;
      parts.push({
        x: pt.u, y: pt.v, vx: Math.cos(angle) * spd, vy: Math.sin(angle) * spd - 2,
        radius: 2.5 + Math.random() * 3.5, color: Math.random() > 0.35 ? '#facc15' : '#34d399',
        alpha: 1, decay: 0.03 + Math.random() * 0.02
      });
    }
    gs.particles = parts;

    gs.ret = createReturn({ x: ball.x, y: Math.max(ball.y, 0.6), z: ball.z }, athlete.swing || 0);
    gs.status = 'BALL_TO_MOUSE';
    gs.startTime = Date.now();
    gs.flightDuration = getFlightDuration() * 0.8;
    gs.progress = 0;

    const basePts = strokeName === 'Saque' ? 150 : (strokeName === 'Backhand' ? 120 : 100);
    const awarded = Math.round(basePts * qualityScore * localComboMultiplier);
    setLocalScore(prev => prev + awarded);
    setLocalRallyCount(prev => prev + 1);
    setLocalComboStreak(prev => {
      const next = prev + 1;
      if (next === 3 || next === 5 || next === 8) playComboSound();
      if (next >= 8) setLocalComboMultiplier(3.0);
      else if (next >= 5) setLocalComboMultiplier(2.0);
      else if (next >= 3) setLocalComboMultiplier(1.5);
      return next;
    });

    logger.info('STROKE-HIT', 'Rebatida validada no ar com sucesso!', {
      golpe: strokeName,
      pontosGanhos: awarded,
      qualityScore,
      comboStreak: localComboStreak + 1,
      multiplicador: localComboMultiplier,
      devolucaoX: Number(gs.ret.x1.toFixed(2))
    });

    setHudStatus({
      text: `⚡ REBATIDA NO AR (${strokeName.toUpperCase()})! +${awarded} pts • ${gs.ret.x1 > 0 ? 'devolvida à direita' : 'devolvida à esquerda'}`,
      color: '#4ade80'
    });
  }, [getFlightDuration, localComboMultiplier, localComboStreak]);

  // IA de visão: rebatida da bola pelo atleta (vida só é descontada se errar a bola, NUNCA por erro de movimento)
  useEffect(() => {
    if (!telemetry || !telemetry.event_id) return;
    if (telemetry.event_id === lastProcessedEventIdRef.current) return;
    lastProcessedEventIdRef.current = telemetry.event_id;

    const detectedStroke = telemetry.stroke_name;
    const failedJoints = telemetry.failed_joints || [];
    const gs = gameStateRef.current;
    if (gs.status !== 'BALL_TO_ATHLETE' || gs.missed || !gs.shot) {
      logger.debug('STROKE-REJECT', 'Golpe ignorado: nenhuma bola em aproximação no momento', {
        golpe: detectedStroke,
        statusJogo: gs.status,
        missed: gs.missed
      });
      return;
    }
    if (!['Forehand', 'Backhand', 'Saque'].includes(detectedStroke)) {
      logger.debug('STROKE-REJECT', 'Golpe ignorado: movimento classificado como Repouso ou nulo', {
        golpe: detectedStroke
      });
      return;
    }

    const athlete = athleteRef.current;
    const ball = sampleShot(gs.shot, gs.progress);

    // Muito cedo: antes do quique (ainda no primeiro arco da trajetória)
    if (ball.phase === 'pre') {
      logger.warn('STROKE-REJECT', 'Golpe ANTECIPADO (TOO_EARLY): bola ainda não quicou no chão da quadra', {
        golpe: detectedStroke,
        faseBola: ball.phase,
        ballZ: Number(ball.z.toFixed(2)),
        bounceZ: Number(gs.shot.z1.toFixed(2))
      });
      setHudStatus({
        text: `⏳ Quase! Aguarde a bola quicar no chão para rebater.`,
        color: '#facc15'
      });
      return;
    }

    // Janela de profundidade Z: atleta pode golpear desde a aproximação até quando ela passa pelo corpo
    const distZ = Math.abs(ball.z - athlete.z);
    const inHitDepth = (ball.z >= athlete.z - HIT_Z_TOLERANCE) && (ball.z <= Math.min(ROOM.zBack, athlete.z + HIT_Z_TOLERANCE));
    if (!inHitDepth) {
      logger.warn('STROKE-REJECT', 'Golpe fora da janela de profundidade Z', {
        golpe: detectedStroke,
        distZ: Number(distZ.toFixed(2)),
        toleranciaZ: HIT_Z_TOLERANCE,
        ballZ: Number(ball.z.toFixed(2)),
        athleteZ: Number(athlete.z.toFixed(2))
      });
      return;
    }

    // Alcance lateral: mão precisa estar perto da bola
    const distWristX = Math.abs(ball.x - athlete.wristX);
    const distBodyX = Math.abs(ball.x - athlete.x);
    if (distWristX > HIT_REACH && distBodyX > HIT_REACH) {
      logger.warn('STROKE-REJECT', 'Golpe fora do alcance lateral X (raquete longe da bola)', {
        golpe: detectedStroke,
        distWristX: Number(distWristX.toFixed(2)),
        distBodyX: Number(distBodyX.toFixed(2)),
        alcanceMaxX: HIT_REACH,
        ballX: Number(ball.x.toFixed(2)),
        wristX: Number(athlete.wristX.toFixed(2))
      });
      return;
    }

    // ATLETA ACERTOU A BOLA: A rebatida acontece!
    // A vida NUNCA é subtraída por falha biomecânica/postural ou golpe diferente
    const qualityScore = telemetry.quality_score ?? (failedJoints.length > 0 ? 0.75 : 1.0);
    returnBallToMouse(detectedStroke, qualityScore);

    if (failedJoints.length > 0) {
      // Alerta postural educativo mantendo o jogo e as vidas intactas
      setHudStatus({
        text: `⚡ REBATIDA COM AJUSTE TÉCNICO: ${detectedStroke.toUpperCase()} (${failedJoints.join(', ')})`,
        color: '#fbbf24'
      });
    }
  }, [telemetry, returnBallToMouse]);

  const getAim = () => mouseToAim(mousePosRef.current.x, mousePosRef.current.y);

  useEffect(() => { athleteDetectedRef.current = athleteDetected; }, [athleteDetected]);
  useEffect(() => { presenceStateRef.current = presenceState; }, [presenceState]);
  useEffect(() => { telemetryRef.current = telemetry; }, [telemetry]);
  useEffect(() => { calibStateRef.current = calibState; }, [calibState]);
  useEffect(() => { gameModeRef.current = gameMode; }, [gameMode]);

  useEffect(() => {
    if (externalLives !== undefined && externalLives > 0 && presenceStateRef.current === 'READY' && !pendingGameOverRef.current) {
      setLocalLives(externalLives);
    }
    if (externalScore !== undefined) setLocalScore(externalScore);
    if (externalCombo !== undefined) setLocalComboStreak(externalCombo);
    if (externalMultiplier !== undefined) setLocalComboMultiplier(externalMultiplier);
    if (externalRally !== undefined) setLocalRallyCount(externalRally);
    if (externalGameOver !== undefined && !pendingGameOverRef.current) {
      setIsGameOverLocal(externalGameOver);
    }
  }, [externalLives, externalScore, externalCombo, externalMultiplier, externalRally, externalGameOver]);

  // Gerenciamento da presença do atleta e contagem regressiva obrigatória de 8 segundos antes da 1ª bola
  useEffect(() => {
    if (!athleteDetected) {
      setPresenceState(prev => {
        if (prev === 'READY' || prev === 'COUNTDOWN_8S') {
          logger.warn('PRESENCE', 'Atleta saiu do campo de visão da câmera! Jogo pausado imediatamente.', {
            estadoAnterior: prev
          });
          return 'PAUSED_NO_ATHLETE';
        }
        return 'WAITING_ATHLETE';
      });
      countdownStartRef.current = null;
      setCountdownRemaining(8);
      botNextLaunchTimeRef.current = 0;
      setHudStatus({
        text: '👤 AGUARDANDO ATLETA: Posicione-se em frente à câmera para iniciar!',
        color: '#facc15'
      });
      return;
    }

    // Atleta entrou no campo de visão:
    if (presenceStateRef.current === 'WAITING_ATHLETE' || presenceStateRef.current === 'PAUSED_NO_ATHLETE') {
      logger.info('PRESENCE', 'Atleta detectado em campo! Iniciando contagem de preparação de 8 segundos.');
      setPresenceState('COUNTDOWN_8S');
      countdownStartRef.current = Date.now();
      setCountdownRemaining(8);
      botNextLaunchTimeRef.current = 0;
    }
  }, [athleteDetected]);

  // Contagem regressiva de 8 segundos
  useEffect(() => {
    if (presenceState !== 'COUNTDOWN_8S') return;

    let lastLoggedSec = -1;
    const interval = setInterval(() => {
      if (!countdownStartRef.current) return;
      const elapsed = (Date.now() - countdownStartRef.current) / 1000;
      const remaining = Math.max(0, 8 - elapsed);
      const remSeconds = Math.ceil(remaining);
      setCountdownRemaining(remSeconds);

      if (remSeconds !== lastLoggedSec) {
        lastLoggedSec = remSeconds;
        logger.debug('PRESENCE', `Preparação do atleta: ${remSeconds}s restantes para liberar quadra`);
      }

      setHudStatus({
        text: `⏱️ ATLETA EM CAMPO! PREPARE-SE: ${remSeconds}s para a primeira bola...`,
        color: '#38bdf8'
      });

      if (remaining <= 0) {
        clearInterval(interval);
        logger.info('PRESENCE', 'Contagem de 8 segundos concluída com sucesso! Quadra liberada para lançamentos.');
        setPresenceState('READY');
        setCountdownRemaining(0);
        setLocalLives(maxLives);
        pendingGameOverRef.current = false;
        setIsGameOverLocal(false);
        gameStateRef.current.missed = false;
        gameStateRef.current.status = 'BALL_WITH_MOUSE';
        if (gameModeRef.current === 'bot') {
          scheduleBotLaunch(1200);
        } else {
          setHudStatus(START_HUD_PVP);
        }
      }
    }, 100);

    return () => clearInterval(interval);
  }, [presenceState, scheduleBotLaunch]);

  const handleCanvasClick = (e) => {
    if (isGameOverLocal) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    mousePosRef.current = { x: (e.clientX - rect.left) / rect.width, y: (e.clientY - rect.top) / rect.height, isInside: true };

    if (gameStateRef.current.status === 'BALL_WITH_MOUSE') {
      if (gameMode === 'bot') {
        // No modo Robô, o clique funciona como disparo rápido ("Lançar Agora")
        botLaunchedRef.current = true;
        launchBall(botAimRef.current);
      } else {
        launchBall(getAim());
      }
    }
  };

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    mousePosRef.current = { x: (e.clientX - rect.left) / rect.width, y: (e.clientY - rect.top) / rect.height, isInside: true };
  };

  // Espaço: atalho de teste
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
      if (e.code === 'Space') {
        e.preventDefault();
        const gs = gameStateRef.current;
        if (gs.status === 'BALL_WITH_MOUSE') {
          if (gameMode === 'bot') {
            botLaunchedRef.current = true;
            launchBall(botAimRef.current);
          } else {
            launchBall(mouseToAim(mousePosRef.current.x, clamp(mousePosRef.current.y, 0.45, 0.75)));
          }
        } else if (gs.status === 'BALL_TO_ATHLETE' && !gs.missed) {
          const ball = sampleShot(gs.shot, gs.progress);
          if (ball.phase === 'post') returnBallToMouse('Forehand', 1.0);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [gameMode, launchBall, returnBallToMouse]);

  // Modo Robô: monitoramento e disparo autônomo da bola
  useEffect(() => {
    if (gameMode !== 'bot' || isGameOverLocal || calibState !== 'READY') return;
    const interval = setInterval(() => {
      const gs = gameStateRef.current;
      const now = Date.now();

      // Robô NUNCA lança se o atleta não estiver pronto (timer de 8s concluído)!
      if (presenceStateRef.current !== 'READY') return;

      if (gs.status === 'BALL_WITH_MOUSE' && !botLaunchedRef.current && botNextLaunchTimeRef.current > 0) {
        if (now >= botNextLaunchTimeRef.current) {
          botLaunchedRef.current = true;
          launchBall(botAimRef.current);
        }
      }
    }, 80);
    return () => clearInterval(interval);
  }, [gameMode, isGameOverLocal, calibState, launchBall]);

  // Loop de render
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let running = true;

    const drawBall = (px, radius, glow = '#facc15', sx = 1, sy = 1) => {
      ctx.save();
      ctx.shadowColor = glow;
      ctx.shadowBlur = 14;
      ctx.beginPath();
      ctx.ellipse(px.u, px.v, radius * sx, radius * sy, 0, 0, Math.PI * 2);
      const g = ctx.createRadialGradient(px.u - radius * 0.3, px.v - radius * 0.3, radius * 0.1, px.u, px.v, radius);
      g.addColorStop(0, '#fef08a'); g.addColorStop(0.7, '#eab308'); g.addColorStop(1, '#a16207');
      ctx.fillStyle = g;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.lineWidth = Math.max(1, radius * 0.08);
      ctx.beginPath();
      ctx.arc(px.u - radius * 0.2, px.v, radius * 0.65, -0.6 * Math.PI, 0.6 * Math.PI);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(px.u + radius * 0.2, px.v, radius * 0.65, 0.4 * Math.PI, 1.6 * Math.PI);
      ctx.stroke();
      ctx.restore();
    };

    const drawShadow = (px, radius, alpha = 0.4) => {
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(px.u, px.floorV, radius * 1.1, radius * 0.4, 0, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,0,0,${alpha})`;
      ctx.fill();
      ctx.restore();
    };

    const render = () => {
      if (!running) return;
      const w = canvas.width;
      const h = canvas.height;
      const now = Date.now();
      const gs = gameStateRef.current;
      const c = calibRef.current;
      const proj = (x, y, z) => project3DTo2D(x, y, z, c, w, h);

      ctx.clearRect(0, 0, w, h);
      if (gs.shakeFrames > 0) {
        ctx.save();
        ctx.translate((Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6);
        gs.shakeFrames--;
      }

      // Atleta em 3D (metros) — a sala NÃO se move com ele
      const ath = estimateAthlete3D(telemetryRef.current?.landmarks, c);
      if (ath) athleteRef.current = ath;
      const athlete = athleteRef.current;

      // Quadra 3D fixa no cômodo
      if (courtMode === 'floor') {
        const line = (a, b) => {
          const p1 = proj(a[0], 0, a[1]);
          const p2 = proj(b[0], 0, b[1]);
          ctx.moveTo(p1.u, p1.floorV);
          ctx.lineTo(p2.u, p2.floorV);
        };
        const xs = 1.65, zb = ROOM.zBackLine, zs = ROOM.zService, zf = 0.9;
        const aim = mousePosRef.current.isInside ? getAim() : null;
        ctx.save();
        if (aim && aim.inBounds && gs.status === 'BALL_WITH_MOUSE') {
          const q = aim.x > 0 ? [0, xs] : [-xs, 0];
          const pts = [[q[0], zs], [q[1], zs], [q[1], zb], [q[0], zb]].map(([x, z]) => proj(x, 0, z));
          ctx.beginPath();
          pts.forEach((p, i) => (i ? ctx.lineTo(p.u, p.floorV) : ctx.moveTo(p.u, p.floorV)));
          ctx.closePath();
          ctx.fillStyle = 'rgba(56,189,248,0.10)';
          ctx.fill();
        }
        ctx.strokeStyle = 'rgba(56,189,248,0.5)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        line([-xs, zb], [xs, zb]);
        line([-xs, zs], [xs, zs]);
        line([-xs, zf], [xs, zf]);
        line([-xs, zf], [-xs, zb]);
        line([xs, zf], [xs, zb]);
        ctx.stroke();
        ctx.strokeStyle = 'rgba(56,189,248,0.3)';
        ctx.beginPath();
        line([0, zs], [0, zb]);
        ctx.stroke();
        ctx.restore();
      }

      // Anéis de quique
      if (bounceRingsRef.current.length > 0) {
        ctx.save();
        bounceRingsRef.current.forEach(ring => {
          ring.r += 2.2;
          ring.alpha -= 0.04;
          if (ring.alpha > 0) {
            ctx.beginPath();
            ctx.ellipse(ring.x, ring.y, ring.r, ring.r * 0.35, 0, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(250,204,21,${ring.alpha})`;
            ctx.lineWidth = 2.5;
            ctx.stroke();
          }
        });
        bounceRingsRef.current = bounceRingsRef.current.filter(r => r.alpha > 0);
        ctx.restore();
      }

      // Máquina de estados
      if (!isGameOverLocal) {
        if (gs.status === 'BALL_TO_ATHLETE' && gs.shot) {
          gs.progress = (now - gs.startTime) / 1000 / gs.flightDuration;
          const ball = sampleShot(gs.shot, Math.min(gs.progress, 1));

          // A bola só é considerada perdida quando passa completamente da profundidade de alcance do atleta
          // e atinge o fim do voo no chão do fundo (Z = 3,45m)
          const passedAthlete = ball.phase === 'post' && (ball.z > athlete.z + HIT_Z_TOLERANCE);
          const reachedEnd = gs.progress >= 1.0;

          if (!gs.missed && (reachedEnd || (passedAthlete && gs.progress >= 0.88))) {
            gs.missed = true; // Desconta estritamente 1 vida ao errar a bola
            logger.warn('GAME-MISS', 'Bola perdida pelo atleta (passou ao fundo da quadra sem rebatida)', {
              zBola: Number(ball.z.toFixed(2)),
              zAtleta: Number(athlete.z.toFixed(2)),
              progress: Number(gs.progress.toFixed(2)),
              fase: ball.phase,
              fimDoVoo: reachedEnd
            });
            deductLife('BALL_MISSED', '❌ BOLA PERDIDA! A bola foi ao fundo e você não rebateu (-1 Vida)');
          }

          if (gs.progress >= 1.0) {
            gs.status = 'FAULT_RESULT';
            gs.lastEventTime = now;
            gs.shakeFrames = 8;
          }
        } else if (gs.status === 'BALL_TO_MOUSE') {
          gs.progress = (now - gs.startTime) / 1000 / gs.flightDuration;
          if (gs.progress >= 1.0) {
            if (gameModeRef.current === 'bot') {
              // Robô defende a bola devolvida pelo atleta e sorteia o próximo alvo
              playHitSound();
              logger.info('BOT-AI', 'Robô interceptou a devolução na rede e preparou novo arremesso!');
              gs.status = 'BALL_WITH_MOUSE';
              scheduleBotLaunch();
            } else {
              const near = Math.abs(getAim().x - gs.ret.x1) <= 0.7;
              gs.status = 'BALL_WITH_MOUSE';
              setHudStatus({
                text: near ? '🎾 Bola defendida! Lance de novo.' : '🎾 Bola recebida! Lance o próximo ponto.',
                color: '#38bdf8'
              });
            }
          }
        } else if (gs.status === 'FAULT_RESULT') {
          if (now - gs.lastEventTime > 1400) {
            if (pendingGameOverRef.current) {
              pendingGameOverRef.current = false;
              setIsGameOverLocal(true);
              logger.error('GAME-MISS', 'FIM DE PARTIDA (GAME OVER) — Bola tocou o fundo da quadra e vidas esgotadas!');
            } else {
              gs.status = 'BALL_WITH_MOUSE';
              if (gameModeRef.current === 'bot') {
                scheduleBotLaunch(1600);
              } else {
                setHudStatus(START_HUD_PVP);
              }
            }
          }
        }
      }

      // Bola com o mouse / Robô (primeiro plano)
      if (gs.status === 'BALL_WITH_MOUSE' && !isGameOverLocal && calibStateRef.current === 'READY') {
        const isBot = gameModeRef.current === 'bot';
        const aim = isBot ? botAimRef.current : getAim();

        if (isBot) {
          // --- RENDERIZAÇÃO DA MIRA DO ROBÔ NO CHÃO DA QUADRA ---
          const target = proj(aim.x, 0, clamp(aim.z, 1.0, 3.3));
          ctx.save();
          const radarPulse = 18 + Math.sin(now * 0.008) * 4;

          // Círculo externo pulsante violeta neon
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(192, 132, 252, 0.85)';
          ctx.lineWidth = 2.5;
          ctx.ellipse(target.u, target.floorV, radarPulse, radarPulse * 0.38, 0, 0, Math.PI * 2);
          ctx.stroke();

          // Círculo interno ciano
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.7)';
          ctx.lineWidth = 1.5;
          ctx.ellipse(target.u, target.floorV, 10, 4, 0, 0, Math.PI * 2);
          ctx.stroke();

          // Mira em cruz fina
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(192, 132, 252, 0.6)';
          ctx.lineWidth = 1.5;
          ctx.moveTo(target.u - 24, target.floorV);
          ctx.lineTo(target.u + 24, target.floorV);
          ctx.moveTo(target.u, target.floorV - 10);
          ctx.lineTo(target.u, target.floorV + 10);
          ctx.stroke();

          // Feixe vertical tracejado do piso
          ctx.beginPath();
          ctx.strokeStyle = 'rgba(192, 132, 252, 0.4)';
          ctx.setLineDash([4, 4]);
          ctx.moveTo(target.u, target.floorV);
          ctx.lineTo(target.u, target.floorV - 45);
          ctx.stroke();
          ctx.setLineDash([]);

          // Badge holográfico com identificação do alvo sorteado
          const sideName = aim.x > 0.3 ? 'DIREITA' : (aim.x < -0.3 ? 'ESQUERDA' : 'CENTRO');
          ctx.font = '900 11px Inter, sans-serif';
          ctx.fillStyle = '#f5d0fe';
          ctx.textAlign = 'center';
          ctx.fillText(`🤖 ALVO DO ROBÔ (${sideName} • ${describeDepth(aim.z)})`, target.u, target.floorV + 22);
          ctx.restore();

          // Bola no primeiro plano (posse do Robô)
          const px = { u: w * 0.5 + Math.sin(now * 0.003) * 18, v: 0.74 * h };
          drawBall(px, 24, '#c084fc');

          // Contagem regressiva e barra de progresso do lançamento do robô
          const remSec = Math.max(0, ((botNextLaunchTimeRef.current - now) / 1000)).toFixed(1);
          ctx.save();
          ctx.font = 'bold 12px Inter, sans-serif';
          ctx.fillStyle = '#f5d0fe';
          ctx.textAlign = 'center';
          ctx.fillText(`🤖 ROBÔ LANÇANDO EM ${remSec}s`, px.u, px.v - 38);

          const totalDur = botPrepareDurationRef.current || 1700;
          const elapsed = totalDur - Math.max(0, botNextLaunchTimeRef.current - now);
          const pct = clamp(elapsed / totalDur, 0, 1);
          ctx.fillStyle = 'rgba(15, 23, 42, 0.7)';
          ctx.fillRect(px.u - 45, px.v - 30, 90, 5);
          ctx.fillStyle = '#c084fc';
          ctx.fillRect(px.u - 45, px.v - 30, 90 * pct, 5);

          ctx.font = '10px Inter, sans-serif';
          ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
          ctx.fillText('Clique p/ lançar agora ⚡', px.u, px.v + 36);
          ctx.restore();

        } else {
          // --- MODO MULTIPLAYER (HUMANO NO MOUSE) ---
          const mx = mousePosRef.current.isInside ? mousePosRef.current.x : 0.5;
          const my = mousePosRef.current.isInside ? mousePosRef.current.y : 0.6;
          const px = { u: mx * w, v: clamp(my, 0.2, 0.92) * h };

          if (mousePosRef.current.isInside) {
            const target = proj(aim.x, 0, clamp(aim.z, 1.0, 3.3));
            ctx.save();
            ctx.strokeStyle = aim.inBounds ? 'rgba(56,189,248,0.8)' : 'rgba(249,115,22,0.8)';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.ellipse(target.u, target.floorV, 16, 6, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.font = 'bold 11px Inter, sans-serif';
            ctx.fillStyle = aim.inBounds ? '#bae6fd' : '#fdba74';
            ctx.textAlign = 'center';
            ctx.fillText(describeDepth(aim.z), target.u, target.floorV + 18);
            ctx.restore();
          }
          drawBall(px, 24, '#38bdf8');
          ctx.save();
          ctx.font = 'bold 12px Inter, sans-serif';
          ctx.fillStyle = '#fde047';
          ctx.textAlign = 'center';
          ctx.fillText('🖱️ CLIQUE P/ LANÇAR', px.u, px.v - 34);
          ctx.restore();
        }
      }

      // Bola rumo ao atleta (3D)
      if (gs.status === 'BALL_TO_ATHLETE' && gs.shot) {
        const p = Math.min(gs.progress, 1);
        const b = sampleShot(gs.shot, p);
        const pt = proj(b.x, b.y, b.z);

        if (b.phase === 'post' && !gs.bouncedMid) {
          gs.bouncedMid = true;
          playBounceSound();
          const bp = proj(gs.shot.x1, 0, gs.shot.z1);
          bounceRingsRef.current.push({ x: bp.u, y: bp.floorV, r: 8, alpha: 0.95 });
        }
        if (p >= 1 && !gs.bouncedBack) {
          gs.bouncedBack = true;
          playBounceSound();
          bounceRingsRef.current.push({ x: pt.u, y: pt.floorV, r: 6, alpha: 0.8 });
        }
        const justBounced = b.phase === 'post' && b.v < 0.06;
        drawShadow(pt, pt.radiusPx, clamp(0.55 - b.y * 0.3, 0.2, 0.55));
        drawBall(pt, pt.radiusPx, '#facc15', justBounced ? 1.25 : 1, justBounced ? 0.72 : 1);

        // indicador sutil da janela de rebatida
        if (!gs.missed && b.phase === 'post' && Math.abs(b.z - athlete.z) <= HIT_Z_TOLERANCE) {
          ctx.save();
          ctx.font = '900 14px Inter, sans-serif';
          ctx.fillStyle = '#4ade80';
          ctx.textAlign = 'center';
          ctx.fillText('⚡ REBATA!', pt.u, pt.v - pt.radiusPx - 10);
          ctx.restore();
        }
      }

      // Devolução ao mouse (3D)
      if (gs.status === 'BALL_TO_MOUSE' && gs.ret) {
        const p = Math.min(gs.progress, 1);
        const b = sampleReturn(gs.ret, p);
        const pt = proj(b.x, b.y, b.z);
        drawShadow(pt, pt.radiusPx, 0.35);
        drawBall(pt, pt.radiusPx, '#34d399');
      }

      // Partículas
      if (gs.particles.length > 0) {
        ctx.save();
        gs.particles.forEach(p => {
          p.x += p.vx; p.y += p.vy; p.alpha -= p.decay;
          if (p.alpha > 0) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.globalAlpha = Math.max(0, p.alpha);
            ctx.fill();
          }
        });
        gs.particles = gs.particles.filter(p => p.alpha > 0);
        ctx.restore();
      }

      // Overlay central de Presença / Timer de 8 segundos
      if (presenceStateRef.current === 'COUNTDOWN_8S') {
        ctx.save();
        ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
        const cardW = 340, cardH = 150;
        const cardX = (w - cardW) / 2, cardY = (h - cardH) / 2;
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(cardX, cardY, cardW, cardH, 16) : ctx.rect(cardX, cardY, cardW, cardH);
        ctx.fill();
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.font = 'bold 13px Inter, sans-serif';
        ctx.fillStyle = '#bae6fd';
        ctx.textAlign = 'center';
        ctx.fillText('⏱️ ATLETA EM CAMPO! PREPARE-SE', w / 2, cardY + 32);

        const rem = countdownRemaining;
        ctx.font = '900 46px Inter, sans-serif';
        ctx.fillStyle = '#38bdf8';
        ctx.fillText(`${rem}`, w / 2, cardY + 86);

        ctx.font = '11px Inter, sans-serif';
        ctx.fillStyle = '#94a3b8';
        ctx.fillText('A 1ª bola será arremessada em instantes...', w / 2, cardY + 120);
        ctx.restore();
      } else if (presenceStateRef.current === 'WAITING_ATHLETE') {
        ctx.save();
        ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
        const cardW = 320, cardH = 100;
        const cardX = (w - cardW) / 2, cardY = (h - cardH) / 2;
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(cardX, cardY, cardW, cardH, 14) : ctx.rect(cardX, cardY, cardW, cardH);
        ctx.fill();
        ctx.strokeStyle = 'rgba(250, 204, 21, 0.5)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.font = 'bold 13px Inter, sans-serif';
        ctx.fillStyle = '#fef08a';
        ctx.textAlign = 'center';
        ctx.fillText('👤 AGUARDANDO ATLETA EM CAMPO', w / 2, cardY + 42);

        ctx.font = '11px Inter, sans-serif';
        ctx.fillStyle = '#cbd5e1';
        ctx.fillText('Entre no enquadramento para iniciar a contagem (8s)', w / 2, cardY + 70);
        ctx.restore();
      } else if (presenceStateRef.current === 'PAUSED_NO_ATHLETE') {
        ctx.save();
        ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
        const cardW = 320, cardH = 100;
        const cardX = (w - cardW) / 2, cardY = (h - cardH) / 2;
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(cardX, cardY, cardW, cardH, 14) : ctx.rect(cardX, cardY, cardW, cardH);
        ctx.fill();
        ctx.strokeStyle = '#f87171';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.font = 'bold 13px Inter, sans-serif';
        ctx.fillStyle = '#fca5a5';
        ctx.textAlign = 'center';
        ctx.fillText('⏸️ JOGO PAUSADO', w / 2, cardY + 42);

        ctx.font = '11px Inter, sans-serif';
        ctx.fillStyle = '#cbd5e1';
        ctx.fillText('Atleta saiu do campo de visão da câmera', w / 2, cardY + 70);
        ctx.restore();
      }

      if (gs.shakeFrames <= 0) ctx.restore();
      animFrameIdRef.current = requestAnimationFrame(render);
    };

    animFrameIdRef.current = requestAnimationFrame(render);
    return () => {
      running = false;
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
    };
  }, [isGameOverLocal, deductLife, courtMode]);

  const statusLabel = gameStateRef.current.status === 'BALL_WITH_MOUSE'
    ? (gameMode === 'bot' ? '🤖 Robô Treinador IA' : 'Jogador do Mouse')
    : gameStateRef.current.status === 'BALL_TO_ATHLETE' ? 'Bola em Jogo' : 'Devolução do Atleta';

  const pill = {
    background: 'rgba(15, 23, 42, 0.88)', backdropFilter: 'blur(10px)',
    borderRadius: '8px', padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '8px'
  };

  return (
    <div
      onClick={handleCanvasClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => { mousePosRef.current.isInside = false; }}
      style={{ position: 'absolute', inset: 0, pointerEvents: 'auto', cursor: 'crosshair', overflow: 'hidden' }}
    >
      <canvas ref={canvasRef} width={800} height={600} style={{ width: '100%', height: '100%', display: 'block' }} />

      <div style={{
        position: 'absolute', top: '12px', left: '14px', right: '14px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px', pointerEvents: 'none'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', pointerEvents: 'auto', flexWrap: 'wrap' }}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              const nextMode = gameMode === 'bot' ? 'multiplayer' : 'bot';
              setGameMode(nextMode);
              if (nextMode === 'bot') {
                scheduleBotLaunch(1200);
              } else {
                botNextLaunchTimeRef.current = 0;
                setHudStatus(START_HUD_PVP);
              }
            }}
            className="btn btn-secondary"
            style={{
              padding: '6px 12px', fontSize: '0.75rem', borderRadius: '8px',
              background: gameMode === 'bot' ? 'rgba(192, 132, 252, 0.25)' : 'rgba(16, 185, 129, 0.25)',
              border: `1px solid ${gameMode === 'bot' ? '#c084fc' : '#10b981'}`
            }}
            title="Alternar entre modo contra Robô IA autônomo ou 2 Jogadores (humano no mouse)"
          >
            {gameMode === 'bot' ? <Bot size={14} color="#c084fc" /> : <Users size={14} color="#34d399" />}
            <span style={{ fontWeight: '800', color: gameMode === 'bot' ? '#f5d0fe' : '#d1fae5' }}>
              {gameMode === 'bot' ? '🤖 Modo Robô (Bot IA)' : '👥 2 Jogadores (Mouse)'}
            </span>
          </button>

          {gameMode === 'bot' && gameStateRef.current.status === 'BALL_WITH_MOUSE' && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                botLaunchedRef.current = true;
                launchBall(botAimRef.current);
              }}
              className="btn btn-secondary"
              style={{
                padding: '6px 10px', fontSize: '0.72rem', borderRadius: '8px',
                background: 'rgba(234, 179, 8, 0.25)', border: '1px solid #eab308',
                color: '#fef08a', fontWeight: '800'
              }}
              title="Forçar o robô a lançar a bola agora sem aguardar a contagem regressiva"
            >
              <Zap size={13} color="#facc15" />
              <span>Lançar Agora ⚡</span>
            </button>
          )}

          <button
            onClick={(e) => { e.stopPropagation(); setCourtMode(m => m === 'floor' ? 'clean' : 'floor'); }}
            className="btn btn-secondary"
            style={{
              padding: '6px 12px', fontSize: '0.75rem', borderRadius: '8px',
              background: courtMode === 'floor' ? 'rgba(56, 189, 248, 0.22)' : 'rgba(15, 23, 42, 0.85)',
              border: `1px solid ${courtMode === 'floor' ? '#38bdf8' : 'rgba(255, 255, 255, 0.15)'}`
            }}
          >
            {courtMode === 'floor' ? <Layers size={14} color="#38bdf8" /> : <Sparkles size={14} color="#facc15" />}
            <span style={{ fontWeight: '700' }}>{courtMode === 'floor' ? 'Quadra 3,5m' : 'Visão Limpa'}</span>
          </button>

          <button
            onClick={(e) => { e.stopPropagation(); setCalibState('PROMPT'); }}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.75rem', borderRadius: '8px' }}
            title="Recalibrar a sala de 3,5m"
          >
            <Ruler size={14} color="#f59e0b" />
            <span style={{ fontWeight: '700' }}>Recalibrar</span>
          </button>

          <div style={{ ...pill, border: `1px solid ${gameMode === 'bot' ? 'rgba(192, 132, 252, 0.4)' : 'rgba(56, 189, 248, 0.3)'}` }}>
            {gameMode === 'bot' ? <Bot size={14} color="#c084fc" /> : <MousePointer size={14} color="#38bdf8" />}
            <span style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
              Posse: <strong style={{ color: '#f8fafc' }}>{statusLabel}</strong>
            </span>
          </div>
        </div>

        <div style={{ ...pill, border: '1px solid rgba(255, 255, 255, 0.15)', gap: '10px', pointerEvents: 'auto' }}>
          <Gauge size={14} color="#f59e0b" />
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Intensidade:</span>
          <input
            type="range" min="1" max="4" step="1" value={speedLevel}
            onChange={(e) => { e.stopPropagation(); setSpeedLevel(Number(e.target.value)); }}
            onClick={(e) => e.stopPropagation()}
            style={{ width: '80px', accentColor: '#f59e0b', cursor: 'pointer' }}
          />
          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: speedLevel === 4 ? '#ef4444' : (speedLevel >= 3 ? '#f59e0b' : '#34d399') }}>
            {['', 'Lenta', 'Média', 'Rápida', 'Turbo 🔥'][speedLevel]}
          </span>
        </div>

        <div style={{ ...pill, border: '1px solid rgba(255, 255, 255, 0.12)', gap: '12px', padding: '6px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {Array.from({ length: maxLives }).map((_, i) => (
              <Heart key={i} size={16} color={i < localLives ? '#ef4444' : '#475569'} fill={i < localLives ? '#ef4444' : 'transparent'} />
            ))}
          </div>
          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)' }} />
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Rally: <strong>{localRallyCount}</strong></div>
            <div style={{
              fontSize: '0.82rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '4px',
              color: localComboMultiplier > 1.0 ? '#facc15' : '#34d399'
            }}>
              {localComboMultiplier > 1.0 && <Flame size={12} color="#f59e0b" />}
              {localComboMultiplier.toFixed(1)}x
            </div>
          </div>
        </div>
      </div>

      {calibState === 'READY' && hudStatus && (
        <div style={{
          position: 'absolute', top: '56px', left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(15, 23, 42, 0.92)', backdropFilter: 'blur(10px)',
          border: `1px solid ${hudStatus.color}66`, borderRadius: '20px', padding: '5px 18px',
          fontSize: '0.80rem', fontWeight: '700', color: hudStatus.color,
          boxShadow: '0 4px 16px rgba(0,0,0,0.45)', pointerEvents: 'none', zIndex: 10, whiteSpace: 'nowrap'
        }}>
          {hudStatus.text}
        </div>
      )}

      {/* Calibração guiada de 1 passo */}
      {calibState === 'PROMPT' && (
        <div
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'absolute', top: '64px', left: '50%', transform: 'translateX(-50%)',
            background: 'rgba(15, 23, 42, 0.95)', backdropFilter: 'blur(12px)',
            border: '1px solid rgba(245, 158, 11, 0.6)', borderRadius: '14px', padding: '14px 18px',
            maxWidth: '440px', zIndex: 20, display: 'flex', flexDirection: 'column', gap: '10px', cursor: 'default'
          }}
        >
          <div style={{ fontWeight: '800', color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Ruler size={16} /> Calibração da sala (1 passo)
          </div>
          <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
            Encoste na <strong>parede do fundo</strong> (até 3,5m da câmera), de frente, com cabeça e pés visíveis, e clique em
            “Calibrar agora”. A quadra ficará fixa na sala.
          </div>
          {calibMsg && <div style={{ fontSize: '0.75rem', color: '#fca5a5' }}>{calibMsg}</div>}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.78rem', borderRadius: '8px' }}
              onClick={(e) => { e.stopPropagation(); calibrateNow(); }}>Calibrar agora</button>
            <button className="btn btn-secondary" style={{ padding: '6px 14px', fontSize: '0.78rem', borderRadius: '8px' }}
              onClick={(e) => { e.stopPropagation(); useDefaultRoom(); }}>Usar padrão 3,5m</button>
          </div>
        </div>
      )}

      <div style={{
        position: 'absolute', bottom: '10px', left: '50%', transform: 'translateX(-50%)',
        background: 'rgba(15, 23, 42, 0.88)', backdropFilter: 'blur(8px)', padding: '5px 16px',
        borderRadius: '8px', fontSize: '0.74rem', color: '#cbd5e1', pointerEvents: 'none',
        border: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', alignItems: 'center', gap: '8px',
        whiteSpace: 'nowrap'
      }}>
        {gameMode === 'bot' ? (
          <>
            <span>🤖 <strong>Robô IA:</strong> dita e sorteia aleatoriamente os cantos da quadra</span>
            <span style={{ color: '#475569' }}>•</span>
            <span>🏃 <strong>Atleta:</strong> desloque-se até o quique e rebata no ar</span>
            <span style={{ color: '#475569' }}>•</span>
            <span>⚡ <strong>Disparo rápido:</strong> clique na tela para lançar</span>
          </>
        ) : (
          <>
            <span>🖱️ <strong>Mouse:</strong> lado = esquerda/direita, altura do cursor = curta/média/fundo</span>
            <span style={{ color: '#475569' }}>•</span>
            <span>🏃 <strong>Atleta:</strong> rebata no ar após o quique; se errar a bola cai atrás</span>
          </>
        )}
      </div>

      {isGameOverLocal && (
        <div style={{
          position: 'absolute', inset: 0, background: 'rgba(2, 6, 23, 0.90)', backdropFilter: 'blur(10px)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: '16px', pointerEvents: 'auto'
        }}>
          <div style={{ background: 'rgba(239, 68, 68, 0.2)', border: '2px solid #ef4444', borderRadius: '50%', padding: '20px' }}>
            <AlertCircle size={48} color="#ef4444" />
          </div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: '900', color: '#f8fafc', margin: 0 }}>FIM DE PARTIDA (GAME OVER)</h2>
          <p style={{ fontSize: '0.95rem', color: '#94a3b8', margin: 0, maxWidth: '420px', textAlign: 'center' }}>
            Suas vidas acabaram! Rally de <strong>{localRallyCount}</strong> rebatidas e <strong>{localScore}</strong> pontos!
          </p>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsGameOverLocal(false);
              pendingGameOverRef.current = false;
              setLocalLives(maxLives);
              setLocalRallyCount(0);
              setLocalComboStreak(0);
              gameStateRef.current.status = 'BALL_WITH_MOUSE';
              gameStateRef.current.missed = false;
              if (athleteDetectedRef.current) {
                setPresenceState('COUNTDOWN_8S');
                countdownStartRef.current = Date.now();
                setCountdownRemaining(8);
              } else {
                setPresenceState('WAITING_ATHLETE');
              }
              if (onResetGame) onResetGame();
            }}
            className="btn btn-primary"
            style={{ padding: '12px 28px', fontSize: '1rem', fontWeight: '700', borderRadius: '10px', marginTop: '8px' }}
          >
            Jogar Novamente
          </button>
        </div>
      )}
    </div>
  );
}
