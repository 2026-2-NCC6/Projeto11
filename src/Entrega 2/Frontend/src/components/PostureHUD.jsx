import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldCheck, Flame, Info } from 'lucide-react';

export function PostureHUD({ strokeName, confidence, feedback, failedJoints }) {
  const isApproved = !failedJoints || failedJoints.length === 0;
  const isResting = strokeName === 'Repouso';

  const strokeColors = {
    'Forehand': { border: '#10b981', bg: 'rgba(16, 185, 129, 0.1)', text: '#34d399' },
    'Backhand': { border: '#06b6d4', bg: 'rgba(6, 182, 212, 0.1)', text: '#38bdf8' },
    'Saque': { border: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.1)', text: '#a78bfa' },
    'Repouso': { border: '#64748b', bg: 'rgba(100, 116, 139, 0.1)', text: '#94a3b8' }
  };

  const style = strokeColors[strokeName] || strokeColors['Repouso'];

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Cabeçalho do Card */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
          Classificação IA & Diagnóstico
        </span>
        <span className={`badge ${isResting ? 'badge-slate' : isApproved ? 'badge-green' : 'badge-red'}`}>
          {isResting ? 'Em Espera' : isApproved ? 'Postura Correta' : 'Ajuste Necessário'}
        </span>
      </div>

      {/* Destaque do Golpe Detectado */}
      <div style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: '12px',
        padding: '16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>
            Movimento Identificado
          </span>
          <h2 style={{ fontSize: '1.8rem', fontWeight: '800', color: style.text, margin: '2px 0' }}>
            {strokeName}
          </h2>
          <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
            Janela temporal de 60 frames (2.0s)
          </span>
        </div>

        {/* Confiança */}
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Grau de Confiança</span>
          <div style={{ fontSize: '1.6rem', fontWeight: '800', color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
            {(confidence * 100).toFixed(0)}%
          </div>
          <div style={{
            width: '90px',
            height: '6px',
            background: 'rgba(255,255,255,0.1)',
            borderRadius: '9999px',
            overflow: 'hidden',
            marginTop: '4px'
          }}>
            <div style={{
              width: `${Math.min(100, Math.max(0, confidence * 100))}%`,
              height: '100%',
              background: style.border,
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
      </div>

      {/* Banner de Feedback Biomecânico */}
      <div style={{
        padding: '14px 16px',
        borderRadius: '12px',
        background: isResting 
          ? 'var(--bg-surface-elevated)'
          : isApproved 
            ? 'rgba(16, 185, 129, 0.12)' 
            : 'rgba(239, 68, 68, 0.12)',
        border: `1px solid ${
          isResting 
            ? 'var(--border-subtle)' 
            : isApproved 
              ? 'rgba(16, 185, 129, 0.35)' 
              : 'rgba(239, 68, 68, 0.35)'
        }`,
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        {isResting ? (
          <Info size={22} color="#94a3b8" style={{ flexShrink: 0, marginTop: '2px' }} />
        ) : isApproved ? (
          <CheckCircle2 size={22} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
        ) : (
          <AlertTriangle size={22} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />
        )}

        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: '0.75rem',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: isResting ? '#94a3b8' : isApproved ? '#34d399' : '#f87171'
          }}>
            {isResting ? 'Aguardando Disparo' : isApproved ? 'Parecer Biomecânico Aprovado' : 'Alerta de Correção Articular'}
          </div>
          <p style={{
            fontSize: '0.95rem',
            fontWeight: '600',
            color: '#f8fafc',
            marginTop: '2px'
          }}>
            {feedback || 'Nenhum movimento registrado no momento.'}
          </p>
        </div>
      </div>

      {/* Articulações em Não-Conformidade */}
      {failedJoints && failedJoints.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: '#f87171', fontWeight: '600' }}>
            Desvios detectados em:
          </span>
          {failedJoints.map(joint => (
            <span key={joint} className="badge badge-red" style={{ fontSize: '0.7rem' }}>
              {joint.replace('_', ' ').toUpperCase()}
            </span>
          ))}
        </div>
      )}

    </div>
  );
}
