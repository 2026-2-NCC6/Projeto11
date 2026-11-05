import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, Film, CheckCircle2, AlertTriangle, Gauge } from 'lucide-react';

export function ReplayCard({ latestReplayUrl, telemetry = {} }) {
  const videoRef = useRef(null);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [isPlaying, setIsPlaying] = useState(true);

  // Quando chegar uma nova URL de replay, reinicia o player automaticamente
  useEffect(() => {
    if (videoRef.current && latestReplayUrl) {
      videoRef.current.load();
      videoRef.current.playbackRate = playbackRate;
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  }, [latestReplayUrl]);

  const handleTogglePlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setIsPlaying(true);
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleRestart = () => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = 0;
    videoRef.current.play();
    setIsPlaying(true);
  };

  const handleSpeedChange = (speed) => {
    setPlaybackRate(speed);
    if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const hasFailedJoints = telemetry?.failed_joints && telemetry.failed_joints.length > 0;

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
              Replay do Último Golpe (5s com MediaPipe)
            </h3>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Memória circular com esqueletos e articulações sobrepostos
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
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <video
              ref={videoRef}
              src={latestReplayUrl}
              autoPlay
              loop
              playsInline
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
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
                {telemetry.stroke_name} ({Math.round(telemetry.confidence * 100)}%):{' '}
              </span>
              <span>{telemetry.feedback}</span>
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
            Execute um movimento real (Forehand, Backhand ou Saque) na câmera. O sistema salvará automaticamente os 5 segundos com a sobreposição dos 33 landmarks para análise biomecânica detalhada.
          </p>
        </div>
      )}

    </div>
  );
}
