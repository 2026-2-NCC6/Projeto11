import React from 'react';
import { Flame, Trophy, Heart, Zap, RotateCcw, Award } from 'lucide-react';

export function RallyGameCard({ gameState, onResetRally }) {
  const {
    score = 0,
    lives = 3,
    max_lives = 3,
    rally_count = 0,
    best_rally = 0,
    combo_multiplier = 1.0,
    combo_streak = 0,
    is_game_over = false,
    level = 1,
    rank_title = 'Iniciante',
    xp_progress = 0,
    last_grade = 'NONE',
    last_points = 0,
    last_feedback = ''
  } = gameState || {};

  const getGradeBadge = () => {
    if (last_grade === 'PERFECT') {
      return {
        bg: 'rgba(34, 197, 94, 0.15)',
        border: 'rgba(34, 197, 94, 0.4)',
        color: '#4ade80',
        text: `PERFECT! +${last_points}`
      };
    }
    if (last_grade === 'GOOD') {
      return {
        bg: 'rgba(56, 189, 248, 0.15)',
        border: 'rgba(56, 189, 248, 0.4)',
        color: '#38bdf8',
        text: `GOOD SHOT! +${last_points}`
      };
    }
    if (last_grade === 'FAULT') {
      return {
        bg: 'rgba(239, 68, 68, 0.15)',
        border: 'rgba(239, 68, 68, 0.4)',
        color: '#f87171',
        text: 'FAULT! -1 Vida'
      };
    }
    return null;
  };

  const badge = getGradeBadge();

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)',
      borderRadius: '16px',
      border: is_game_over ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(255, 255, 255, 0.08)',
      padding: '20px',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.36)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      
      {/* Cabeçalho do Card */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
            borderRadius: '8px',
            padding: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Flame size={18} color="#ffffff" />
          </div>
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              Modo Rally Virtual
            </h3>
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Gamificação e Sobrevivência
            </span>
          </div>
        </div>

        {/* Nível e Patente */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{
            background: 'rgba(59, 130, 246, 0.15)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            color: '#60a5fa',
            padding: '4px 10px',
            borderRadius: '20px',
            fontSize: '0.75rem',
            fontWeight: 600
          }}>
            Nv {level} • {rank_title}
          </span>
        </div>
      </div>

      {/* Grid de Métricas do Jogo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
        
        {/* Rally Atual */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          padding: '12px',
          textAlign: 'center'
        }}>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Rally Atual
          </span>
          <div style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            color: rally_count > 0 ? '#4ade80' : '#f8fafc',
            marginTop: '2px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px'
          }}>
            {rally_count}
            {rally_count >= 5 && <Flame size={18} color="#f59e0b" />}
          </div>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            Recorde: {best_rally}
          </span>
        </div>

        {/* Placar & Combo */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          padding: '12px',
          textAlign: 'center'
        }}>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Pontuação
          </span>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#fbbf24', marginTop: '2px' }}>
            {score}
          </div>
          <span style={{
            fontSize: '0.7rem',
            color: combo_multiplier > 1.0 ? '#38bdf8' : '#64748b',
            fontWeight: combo_multiplier > 1.0 ? 600 : 400
          }}>
            Combo x{combo_multiplier.toFixed(1)} ({combo_streak}x)
          </span>
        </div>

        {/* Vidas Restantes */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          padding: '12px',
          textAlign: 'center'
        }}>
          <span style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Vidas
          </span>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '6px', marginTop: '8px' }}>
            {Array.from({ length: max_lives }).map((_, i) => (
              <Heart
                key={i}
                size={20}
                fill={i < lives ? '#ef4444' : 'none'}
                color={i < lives ? '#ef4444' : '#475569'}
                style={{ filter: i < lives ? 'drop-shadow(0 0 6px rgba(239, 68, 68, 0.5))' : 'none' }}
              />
            ))}
          </div>
          <span style={{ fontSize: '0.7rem', color: is_game_over ? '#ef4444' : '#64748b', marginTop: '4px', display: 'block' }}>
            {is_game_over ? 'Fim de Jogo' : `${lives} de ${max_lives} vidas`}
          </span>
        </div>

      </div>

      {/* Barra de Progresso de XP */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '6px' }}>
          <span style={{ color: '#94a3b8' }}>Evolução de Patente</span>
          <span style={{ color: '#60a5fa', fontWeight: 600 }}>{xp_progress}% XP</span>
        </div>
        <div style={{
          width: '100%',
          height: '6px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: `${xp_progress}%`,
            height: '100%',
            background: 'linear-gradient(90deg, #3b82f6, #10b981)',
            borderRadius: '4px',
            transition: 'width 0.4s ease'
          }} />
        </div>
      </div>

      {/* Toast / Feedback do Último Golpe */}
      {badge && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          borderRadius: '10px',
          background: badge.bg,
          border: `1px solid ${badge.border}`,
          marginBottom: '14px'
        }}>
          <span style={{ color: badge.color, fontWeight: 700, fontSize: '0.85rem' }}>
            {badge.text}
          </span>
          <span style={{ color: '#cbd5e1', fontSize: '0.75rem' }}>
            {last_feedback}
          </span>
        </div>
      )}

      {/* Alerta de Game Over ou Botão de Ação */}
      {is_game_over ? (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '10px',
          padding: '12px',
          textAlign: 'center'
        }}>
          <div style={{ color: '#f87171', fontWeight: 700, fontSize: '0.9rem', marginBottom: '8px' }}>
            GAME OVER - Você esgotou suas vidas!
          </div>
          <button
            onClick={onResetRally}
            style={{
              background: 'linear-gradient(135deg, #ef4444, #dc2626)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <RotateCcw size={14} /> Tentar Novamente
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={onResetRally}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
              borderRadius: '8px',
              padding: '6px 12px',
              fontSize: '0.75rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s ease'
            }}
            onMouseOver={(e) => { e.currentTarget.style.color = '#f8fafc'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'; }}
            onMouseOut={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'; }}
          >
            <RotateCcw size={13} /> Reiniciar Rally
          </button>
        </div>
      )}

    </div>
  );
}
