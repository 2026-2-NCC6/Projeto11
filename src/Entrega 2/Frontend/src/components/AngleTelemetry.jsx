import React from 'react';
import { Compass, Check, AlertCircle } from 'lucide-react';

export function AngleTelemetry({ angles = {}, currentStroke }) {
  // Configurações de ângulos biomecânicos e limites recomendados
  const angleMetrics = [
    {
      id: 'elbow_r',
      name: 'Cotovelo Direito',
      value: angles.elbow_r ?? 120,
      target: 'Impacto ideal: > 120° (Forehand)',
      min: 40,
      max: 180,
      isCorrect: currentStroke === 'Forehand' ? (angles.elbow_r ?? 120) >= 120 : true
    },
    {
      id: 'elbow_l',
      name: 'Cotovelo Esquerdo',
      value: angles.elbow_l ?? 120,
      target: 'Impacto ideal: > 110° (Backhand)',
      min: 40,
      max: 180,
      isCorrect: currentStroke === 'Backhand' ? (angles.elbow_l ?? 120) >= 110 : true
    },
    {
      id: 'knee_r',
      name: 'Joelho Direito',
      value: angles.knee_r ?? 150,
      target: 'Flexão saque: < 150° (Impulsão)',
      min: 60,
      max: 180,
      isCorrect: currentStroke === 'Saque' ? (angles.knee_r ?? 150) <= 150 : true
    },
    {
      id: 'knee_l',
      name: 'Joelho Esquerdo',
      value: angles.knee_l ?? 150,
      target: 'Flexão saque: < 150° (Impulsão)',
      min: 60,
      max: 180,
      isCorrect: currentStroke === 'Saque' ? (angles.knee_l ?? 150) <= 150 : true
    }
  ];

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Compass size={18} color="#06b6d4" />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Telemetria de Ângulos 3D (Trigonometria)
          </span>
        </div>
        <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
          Graus Articulares
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
        {angleMetrics.map(item => {
          const percent = Math.min(100, Math.max(0, ((item.value - item.min) / (item.max - item.min)) * 100));

          return (
            <div
              key={item.id}
              style={{
                background: 'var(--bg-surface-elevated)',
                border: `1px solid ${item.isCorrect ? 'var(--border-subtle)' : 'rgba(239, 68, 68, 0.4)'}`,
                borderRadius: '10px',
                padding: '12px 14px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: '600', color: '#cbd5e1' }}>
                  {item.name}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '1.2rem',
                  fontWeight: '700',
                  color: item.isCorrect ? '#34d399' : '#f87171'
                }}>
                  {Math.round(item.value)}°
                </span>
              </div>

              {/* Barra de Progresso do Ângulo */}
              <div style={{
                width: '100%',
                height: '6px',
                background: 'rgba(255, 255, 255, 0.08)',
                borderRadius: '9999px',
                overflow: 'hidden',
                margin: '8px 0 6px 0'
              }}>
                <div style={{
                  width: `${percent}%`,
                  height: '100%',
                  background: item.isCorrect 
                    ? 'linear-gradient(90deg, #10b981, #06b6d4)' 
                    : 'linear-gradient(90deg, #f59e0b, #ef4444)',
                  transition: 'width 0.25s ease'
                }} />
              </div>

              <div style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                {item.isCorrect ? (
                  <Check size={12} color="#10b981" />
                ) : (
                  <AlertCircle size={12} color="#ef4444" />
                )}
                <span>{item.target}</span>
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
