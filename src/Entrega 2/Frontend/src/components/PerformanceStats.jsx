import React from 'react';
import { Target, Award, BarChart3, TrendingUp } from 'lucide-react';

export function PerformanceStats({ stats }) {
  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BarChart3 size={18} color="#10b981" />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Desempenho Geral da Sessão
          </span>
        </div>
        <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>
          Métricas Acumuladas
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
        
        {/* Taxa de Acerto */}
        <div style={{
          background: 'var(--bg-surface-elevated)',
          borderRadius: '12px',
          padding: '14px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Acurácia Postural</span>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: stats.accuracy >= 70 ? '#34d399' : '#fbbf24', fontFamily: 'var(--font-mono)' }}>
            {stats.accuracy}%
          </div>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            {stats.approved} de {stats.total} aprovados
          </span>
        </div>

        {/* Total de Golpes */}
        <div style={{
          background: 'var(--bg-surface-elevated)',
          borderRadius: '12px',
          padding: '14px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total de Golpes</span>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {stats.total}
          </div>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            Identificados pela IA
          </span>
        </div>

        {/* Forehand */}
        <div style={{
          background: 'var(--bg-surface-elevated)',
          borderRadius: '12px',
          padding: '14px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Forehands</span>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#10b981', fontFamily: 'var(--font-mono)' }}>
            {stats.forehands}
          </div>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            Classe 0 (Direita)
          </span>
        </div>

        {/* Backhand */}
        <div style={{
          background: 'var(--bg-surface-elevated)',
          borderRadius: '12px',
          padding: '14px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Backhands</span>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#06b6d4', fontFamily: 'var(--font-mono)' }}>
            {stats.backhands}
          </div>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            Classe 1 (Esquerda)
          </span>
        </div>

        {/* Saque */}
        <div style={{
          background: 'var(--bg-surface-elevated)',
          borderRadius: '12px',
          padding: '14px',
          border: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Saques</span>
          <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#8b5cf6', fontFamily: 'var(--font-mono)' }}>
            {stats.saques}
          </div>
          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
            Classe 2 (Impulsão)
          </span>
        </div>

      </div>

    </div>
  );
}
