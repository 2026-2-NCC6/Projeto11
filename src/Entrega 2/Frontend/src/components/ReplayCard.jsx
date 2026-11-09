import React, { useRef, useState, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Film, 
  CheckCircle2, 
  AlertTriangle, 
  Gauge, 
  Check, 
  X, 
  ShieldAlert, 
  Sparkles, 
  RefreshCw 
} from 'lucide-react';

export function ReplayCard({ latestReplayUrl, telemetry = {} }) {
  const videoRef = useRef(null);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  // Estados de Auditoria e Retreino
  const [auditMessage, setAuditMessage] = useState(null);
  const [auditType, setAuditType] = useState('success');
  const [isAuditing, setIsAuditing] = useState(false);
  const [retrainStatus, setRetrainStatus] = useState('idle');

  // Quando chegar uma nova URL de replay, reinicia o player automaticamente
  useEffect(() => {
    setHasError(false);
    if (videoRef.current && latestReplayUrl) {
      videoRef.current.playbackRate = playbackRate;
      videoRef.current.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.warn("[ReplayCard] Autoplay bloqueado pelo navegador:", err);
        setIsPlaying(false);
      });
    }
  }, [latestReplayUrl, reloadKey]);

  // Atalhos de teclado para auditoria rápida
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignora se estiver digitando em input/textarea
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
      if (!latestReplayUrl) return;

      if (e.key === 'Enter') {
        e.preventDefault();
        handleAudit('confirm', telemetry.stroke_name?.toLowerCase() || 'forehand');
      } else if (e.key === '1') {
        e.preventDefault();
        handleAudit('relabel', 'forehand');
      } else if (e.key === '2') {
        e.preventDefault();
        handleAudit('relabel', 'backhand');
      } else if (e.key === '3') {
        e.preventDefault();
        handleAudit('relabel', 'saque');
      } else if (e.key === '4' || e.key.toLowerCase() === 'f') {
        e.preventDefault();
        handleAudit('false_positive', 'repouso');
      } else if (e.key.toLowerCase() === 'd') {
        e.preventDefault();
        handleAudit('discard', null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [latestReplayUrl, telemetry]);

  const handleTogglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleRestart = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
  };

  const handleRetry = () => {
    setHasError(false);
    setReloadKey(k => k + 1);
  };

  const handleSpeedChange = (speed) => {
    setPlaybackRate(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  // Envio de ação de auditoria
  const handleAudit = async (action, targetClass) => {
    if (isAuditing) return;
    setIsAuditing(true);

    try {
      const res = await fetch('/api/audit/label', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          target_class: targetClass || 'forehand',
          replay_filename: telemetry?.latest_replay_filename || 'replay_latest.mp4'
        })
      });

      const data = await res.json();
      if (res.ok) {
        if (action === 'false_positive') {
          setAuditType('warning');
          setAuditMessage('Falso Positivo enviado para a pasta repouso/ com sucesso!');
        } else if (action === 'discard') {
          setAuditType('neutral');
          setAuditMessage('Clipe descartado sem salvar.');
        } else {
          setAuditType('success');
          setAuditMessage(`Auditado com sucesso: Salvo em ${targetClass.toUpperCase()}!`);
        }
      } else {
        setAuditType('error');
        setAuditMessage(`Erro: ${data.error || 'Falha ao salvar auditoria'}`);
      }
    } catch (err) {
      setAuditType('error');
      setAuditMessage('Erro ao comunicar com o servidor de auditoria.');
    } finally {
      setIsAuditing(false);
      setTimeout(() => setAuditMessage(null), 4000);
    }
  };

  // Disparo de retreino automático
  const handleRetrain = async () => {
    try {
      setRetrainStatus('running');
      const res = await fetch('/api/audit/retrain', { method: 'POST' });
      if (res.ok) {
        // Poll status
        const interval = setInterval(async () => {
          const sRes = await fetch('/api/audit/retrain_status');
          const sData = await sRes.json();
          if (sData.status === 'completed') {
            setRetrainStatus('completed');
            clearInterval(interval);
            setTimeout(() => setRetrainStatus('idle'), 5000);
          } else if (sData.status === 'error') {
            setRetrainStatus('error');
            clearInterval(interval);
            setTimeout(() => setRetrainStatus('idle'), 5000);
          }
        }, 2000);
      }
    } catch (e) {
      setRetrainStatus('error');
      setTimeout(() => setRetrainStatus('idle'), 4000);
    }
  };

  const hasFailedJoints = telemetry?.failed_joints && telemetry.failed_joints.length > 0;
  const strokeName = telemetry?.stroke_name || 'Golpe';

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      
      {/* Cabeçalho do Card */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '8px',
            padding: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Film size={18} color="#38bdf8" />
          </div>
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: '700', margin: 0, color: '#f8fafc' }}>
              Replay de 5s & Auditoria com IA
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Memória circular de 150 frames com qualificação biomecânica contínua
            </span>
          </div>
        </div>

        {latestReplayUrl && (
          <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
            ● Replay Disponível
          </span>
        )}
      </div>

      {/* Conteúdo Principal do Vídeo */}
      {latestReplayUrl ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          
          <div style={{
            position: 'relative',
            width: '100%',
            height: '240px',
            background: '#020617',
            borderRadius: '10px',
            overflow: 'hidden',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            {hasError ? (
              <div style={{ textAlign: 'center', padding: '16px', color: '#f87171' }}>
                <AlertTriangle size={32} style={{ margin: '0 auto 8px auto', display: 'block' }} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
                  Não foi possível reproduzir este clipe no navegador
                </span>
                <button onClick={handleRetry} className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                  <RotateCcw size={12} /> Recarregar Clipe
                </button>
              </div>
            ) : (
              <video
                key={`${latestReplayUrl}_${reloadKey}`}
                ref={videoRef}
                src={latestReplayUrl}
                autoPlay
                loop
                muted
                playsInline
                preload="auto"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onError={(e) => {
                  console.error("[ReplayCard] Erro no player de vídeo:", e);
                  setHasError(true);
                }}
              />
            )}
          </div>

          {/* Controles de Reprodução e Câmera Lenta */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={handleTogglePlay}
                className="btn btn-secondary"
                style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                <span>{isPlaying ? 'Pausar' : 'Reproduzir'}</span>
              </button>

              <button
                onClick={handleRestart}
                className="btn btn-secondary"
                style={{ padding: '6px 10px', fontSize: '0.8rem' }}
                title="Reiniciar Replay"
              >
                <RotateCcw size={14} />
              </button>
            </div>

            {/* Seletor de Câmera Lenta */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(0,0,0,0.3)', padding: '4px 8px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Gauge size={13} color="#94a3b8" />
              <span style={{ fontSize: '0.7rem', color: '#94a3b8', marginRight: '4px' }}>Velocidade:</span>
              {[0.25, 0.5, 1.0].map((speed) => (
                <button
                  key={speed}
                  onClick={() => handleSpeedChange(speed)}
                  style={{
                    background: playbackRate === speed ? '#38bdf8' : 'transparent',
                    color: playbackRate === speed ? '#0f172a' : '#cbd5e1',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '2px 6px',
                    fontSize: '0.7rem',
                    fontWeight: '700',
                    cursor: 'pointer',
                    transition: 'all 0.15s'
                  }}
                >
                  {speed === 1.0 ? '1x' : `${speed}x`}
                </button>
              ))}
            </div>

          </div>

          {/* Diagnóstico Biomecânico do Golpe Gravado */}
          <div style={{
            background: hasFailedJoints ? 'rgba(239, 68, 68, 0.12)' : 'rgba(16, 185, 129, 0.12)',
            border: `1px solid ${hasFailedJoints ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
            borderRadius: '8px',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            {hasFailedJoints ? (
              <AlertTriangle size={18} color="#ef4444" style={{ flexShrink: 0 }} />
            ) : (
              <CheckCircle2 size={18} color="#10b981" style={{ flexShrink: 0 }} />
            )}
            <div style={{ fontSize: '0.82rem', color: '#f1f5f9' }}>
              <span style={{ fontWeight: '700', color: hasFailedJoints ? '#f87171' : '#34d399' }}>
                {telemetry.stroke_name} ({Math.round((telemetry.confidence || 0) * 100)}%):{' '}
              </span>
              <span>{telemetry.feedback}</span>
            </div>
          </div>

          {/* PAINEL DE AUDITORIA & RETREINO */}
          <div style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(56, 189, 248, 0.2)',
            borderRadius: '8px',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: '700', color: '#38bdf8' }}>
                Painel de Auditoria (Esperado vs. Previsto)
              </span>
              <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
                Use as teclas [ENTER], [1], [2], [3], [4/F] ou [D]
              </span>
            </div>

            {/* Notificação de Status de Auditoria */}
            {auditMessage && (
              <div style={{
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '0.76rem',
                fontWeight: '600',
                background: auditType === 'success' ? 'rgba(16, 185, 129, 0.2)' : auditType === 'warning' ? 'rgba(251, 146, 60, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                color: auditType === 'success' ? '#34d399' : auditType === 'warning' ? '#fb923c' : '#cbd5e1',
                border: `1px solid ${auditType === 'success' ? '#10b981' : auditType === 'warning' ? '#f97316' : '#64748b'}`
              }}>
                {auditMessage}
              </div>
            )}

            {/* Botões de Ação */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              {/* Botão de Confirmação */}
              <button
                disabled={isAuditing}
                onClick={() => handleAudit('confirm', strokeName.toLowerCase())}
                style={{
                  background: '#10b981',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 10px',
                  fontSize: '0.78rem',
                  fontWeight: '700',
                  cursor: isAuditing ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <Check size={14} />
                Confirmar {strokeName} [Enter]
              </button>

              {/* Botão Falso Positivo (Repouso) */}
              <button
                disabled={isAuditing}
                onClick={() => handleAudit('false_positive', 'repouso')}
                style={{
                  background: '#ea580c',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 10px',
                  fontSize: '0.78rem',
                  fontWeight: '700',
                  cursor: isAuditing ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <ShieldAlert size={14} />
                Falso Positivo [4 / F]
              </button>
            </div>

            {/* Linha de Correção e Descarte */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.70rem', color: '#94a3b8', marginRight: '4px' }}>Corrigir:</span>
              <button
                disabled={isAuditing}
                onClick={() => handleAudit('relabel', 'forehand')}
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '0.72rem' }}
              >
                Forehand [1]
              </button>
              <button
                disabled={isAuditing}
                onClick={() => handleAudit('relabel', 'backhand')}
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '0.72rem' }}
              >
                Backhand [2]
              </button>
              <button
                disabled={isAuditing}
                onClick={() => handleAudit('relabel', 'saque')}
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '0.72rem' }}
              >
                Saque [3]
              </button>
              <button
                disabled={isAuditing}
                onClick={() => handleAudit('discard', null)}
                className="btn btn-secondary"
                style={{ padding: '4px 8px', fontSize: '0.72rem', color: '#94a3b8', marginLeft: 'auto' }}
              >
                <X size={12} /> Descartar [D]
              </button>
            </div>

            {/* Botão de Retreinamento em 1 Clique */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.70rem', color: '#64748b' }}>
                Atualizar cérebro da IA com os novos dados:
              </span>
              <button
                disabled={retrainStatus === 'running'}
                onClick={handleRetrain}
                style={{
                  background: retrainStatus === 'completed' ? '#059669' : '#0284c7',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '5px 10px',
                  fontSize: '0.72rem',
                  fontWeight: '600',
                  cursor: retrainStatus === 'running' ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {retrainStatus === 'running' ? (
                  <>
                    <RefreshCw size={12} className="spin-animation" />
                    <span>Treinando...</span>
                  </>
                ) : retrainStatus === 'completed' ? (
                  <>
                    <Sparkles size={12} />
                    <span>IA Atualizada!</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={12} />
                    <span>Retreinar IA</span>
                  </>
                )}
              </button>
            </div>

          </div>

        </div>
      ) : (
        /* Estado vazio quando nenhum golpe foi executado ainda */
        <div style={{
          padding: '32px 16px',
          textAlign: 'center',
          background: 'rgba(15, 23, 42, 0.4)',
          borderRadius: '10px',
          border: '1px dashed rgba(255, 255, 255, 0.12)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Film size={28} color="#64748b" />
          <span style={{ fontSize: '0.85rem', fontWeight: '600', color: '#cbd5e1' }}>
            Nenhum replay gravado ainda
          </span>
          <p style={{ fontSize: '0.75rem', color: '#64748b', maxWidth: '380px', margin: 0 }}>
            Execute um movimento real na câmera. O sistema salvará automaticamente os 5 segundos com a sobreposição biomecânica para auditoria imediata.
          </p>
        </div>
      )}

    </div>
  );
}
