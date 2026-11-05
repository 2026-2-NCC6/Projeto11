import React from 'react';
import { Cpu, Radio, CheckCircle, AlertOctagon } from 'lucide-react';

const LED_DEFINITIONS = [
  { id: 'ombro_esq', label: 'Ombro E.', pin: 2, byte: 'A', lm: 11 },
  { id: 'ombro_dir', label: 'Ombro D.', pin: 3, byte: 'B', lm: 12 },
  { id: 'cotovelo_esq', label: 'Cotovelo E.', pin: 4, byte: 'C', lm: 13 },
  { id: 'cotovelo_dir', label: 'Cotovelo D.', pin: 5, byte: 'D', lm: 14 },
  { id: 'pulso_esq', label: 'Pulso E.', pin: 6, byte: 'E', lm: 15 },
  { id: 'pulso_dir', label: 'Pulso D.', pin: 7, byte: 'F', lm: 16 },
  { id: 'quadril_esq', label: 'Quadril E.', pin: 8, byte: 'G', lm: 23 },
  { id: 'quadril_dir', label: 'Quadril D.', pin: 9, byte: 'H', lm: 24 },
  { id: 'joelho_esq', label: 'Joelho E.', pin: 10, byte: 'I', lm: 25 },
  { id: 'joelho_dir', label: 'Joelho D.', pin: 11, byte: 'J', lm: 26 },
  { id: 'tornozelo_esq', label: 'Tornozelo E.', pin: 12, byte: 'K', lm: 27 },
  { id: 'tornozelo_dir', label: 'Tornozelo D.', pin: 13, byte: 'L', lm: 28 },
];

export function IotLedMatrix({ failedJoints = [], isConnected }) {
  const isAnyLedOn = failedJoints && failedJoints.length > 0;

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={18} color="#f59e0b" />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Painel Físico IoT / Arduino (12 LEDs)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className={`badge ${isAnyLedOn ? 'badge-red' : 'badge-green'}`} style={{ fontSize: '0.65rem' }}>
            {isAnyLedOn ? 'Alerta Ativo' : 'Reset [Byte R]'}
          </span>
        </div>
      </div>

      <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
        Mapeamento de atuadores físicos em tempo real (Portas 2 a 13 - COM4 a 9600 baud)
      </p>

      {/* Grid de LEDs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '10px'
      }}>
        {LED_DEFINITIONS.map(led => {
          const isActive = failedJoints.includes(led.id);

          return (
            <div
              key={led.id}
              style={{
                background: isActive 
                  ? 'rgba(239, 68, 68, 0.2)' 
                  : 'var(--bg-surface-elevated)',
                border: `1px solid ${isActive ? '#ef4444' : 'rgba(255, 255, 255, 0.08)'}`,
                borderRadius: '8px',
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? '0 0 15px rgba(239, 68, 68, 0.5)' : 'none'
              }}
            >
              {/* Lâmpada LED */}
              <div style={{
                width: '14px',
                height: '14px',
                borderRadius: '50%',
                backgroundColor: isActive ? '#ef4444' : '#1e293b',
                border: `2px solid ${isActive ? '#fca5a5' : '#475569'}`,
                boxShadow: isActive ? '0 0 10px #ef4444, inset 0 0 4px #fff' : 'none',
                transition: 'all 0.15s ease'
              }} />

              <span style={{ fontSize: '0.7rem', fontWeight: '600', color: isActive ? '#fff' : '#cbd5e1' }}>
                {led.label}
              </span>

              <div style={{ display: 'flex', gap: '4px', fontSize: '0.6rem', color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                <span>P{led.pin}</span>
                <span>•</span>
                <span style={{ color: isActive ? '#f87171' : '#06b6d4' }}>'{led.byte}'</span>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{
        fontSize: '0.7rem',
        color: '#64748b',
        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        paddingTop: '10px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <span>Firmware: <code>firmware_leds.ino</code></span>
        <span>Controle: Anti-gargalo com flag de disparo único</span>
      </div>

    </div>
  );
}
