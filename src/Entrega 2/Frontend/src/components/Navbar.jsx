import React from 'react';
import { Activity, Play, Pause, RotateCcw, Volume2, VolumeX, Radio, Cpu, User } from 'lucide-react';

export function Navbar({
  isConnected,
  isDemoMode,
  sessionActive,
  sessionSeconds,
  lateralidade,
  audioEnabled,
  onToggleSession,
  onResetSession,
  onToggleHandedness,
  onToggleAudio
}) {
  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <header className="glass-panel" style={{ padding: '14px 24px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Marca & Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(16, 185, 129, 0.4)'
          }}>
            <Activity size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: '800', letterSpacing: '-0.02em', color: '#fff' }}>
                Tenni<span style={{ color: '#10b981' }}>Sync</span>
              </h1>
              <span className="badge badge-green" style={{ fontSize: '0.65rem', padding: '2px 8px' }}>
                Entrega 2
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Análise Biomecânica & Visão Computacional em Tempo Real
            </p>
          </div>
        </div>

        {/* Status de Conexão e Timer */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* Status do Backend */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            borderRadius: '9999px',
            background: isConnected ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
            border: `1px solid ${isConnected ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: isConnected ? '#10b981' : '#f59e0b',
              boxShadow: isConnected ? '0 0 8px #10b981' : '0 0 8px #f59e0b'
            }} className="pulse-dot" />
            <span style={{ fontSize: '0.75rem', fontWeight: '600', color: isConnected ? '#34d399' : '#fbbf24' }}>
              {isConnected ? 'Backend Online' : 'Modo Simulação / Demo'}
            </span>
          </div>

          {/* Timer da Sessão */}
          <div style={{
            padding: '6px 14px',
            borderRadius: '8px',
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.9rem',
            color: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ color: '#64748b', fontSize: '0.75rem' }}>DURAÇÃO:</span>
            <strong>{formatTime(sessionSeconds)}</strong>
          </div>
        </div>

        {/* Painel de Controles e Preferências */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          
          {/* Lateralidade (US07) */}
          <button
            onClick={onToggleHandedness}
            className="btn btn-secondary"
            title="Alternar lateralidade do tenista (US07)"
            style={{ fontSize: '0.8rem' }}
          >
            <User size={15} color="#10b981" />
            <span>Mão: <strong>{lateralidade.toUpperCase()}</strong></span>
          </button>

          {/* Áudio / Voz (US10) */}
          <button
            onClick={onToggleAudio}
            className={`btn btn-secondary ${audioEnabled ? 'active' : ''}`}
            title="Instruções de voz em tempo real (US10)"
          >
            {audioEnabled ? <Volume2 size={16} /> : <VolumeX size={16} color="#64748b" />}
            <span style={{ fontSize: '0.8rem' }}>Voz: {audioEnabled ? 'ON' : 'OFF'}</span>
          </button>

          {/* Iniciar / Pausar */}
          <button
            onClick={onToggleSession}
            className={`btn ${sessionActive ? 'btn-danger' : 'btn-primary'}`}
            style={{ minWidth: '110px' }}
          >
            {sessionActive ? (
              <>
                <Pause size={16} />
                <span>Pausar</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Iniciar</span>
              </>
            )}
          </button>

          {/* Resetar */}
          <button
            onClick={onResetSession}
            className="btn btn-secondary"
            title="Reiniciar sessão e métricas"
          >
            <RotateCcw size={16} />
          </button>

        </div>

      </div>
    </header>
  );
}
