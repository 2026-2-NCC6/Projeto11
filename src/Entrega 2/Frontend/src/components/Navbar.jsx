import React from 'react';
import { Activity, Play, Pause, RotateCcw, Volume2, VolumeX, Radio, Cpu, User, Gamepad2, Columns, LayoutDashboard } from 'lucide-react';

export function Navbar({
  isConnected,
  isDemoMode,
  sessionActive,
  sessionSeconds,
  lateralidade,
  audioEnabled,
  viewMode = 'dashboard',
  onChangeViewMode = () => {},
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

        {/* Seletor de Modo de Visualizacao */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '10px',
          padding: '3px',
          gap: '2px'
        }}>
          <button
            onClick={() => onChangeViewMode('fullscreen')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '0.76rem',
              fontWeight: '600',
              borderRadius: '7px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              background: viewMode === 'fullscreen' ? '#10b981' : 'transparent',
              color: viewMode === 'fullscreen' ? '#ffffff' : '#94a3b8'
            }}
            title="Camera Cheia (100% largura) com Jogo Virtual e complementos inferiores"
          >
            <Gamepad2 size={14} />
            <span>Câmera Cheia (Jogo)</span>
          </button>

          <button
            onClick={() => onChangeViewMode('split_iot')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '0.76rem',
              fontWeight: '600',
              borderRadius: '7px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              background: viewMode === 'split_iot' ? '#10b981' : 'transparent',
              color: viewMode === 'split_iot' ? '#ffffff' : '#94a3b8'
            }}
            title="Visao 3/4 Camera + 1/4 Boneco IoT a direita"
          >
            <Columns size={14} />
            <span>3/4 Câmera + IoT</span>
          </button>

          <button
            onClick={() => onChangeViewMode('dashboard')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '0.76rem',
              fontWeight: '600',
              borderRadius: '7px',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              background: viewMode === 'dashboard' ? '#10b981' : 'transparent',
              color: viewMode === 'dashboard' ? '#ffffff' : '#94a3b8'
            }}
            title="Painel analitico modular classico"
          >
            <LayoutDashboard size={14} />
            <span>Painel Clássico</span>
          </button>
        </div>

        {/* Painel de Controles e Preferencias */}
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
