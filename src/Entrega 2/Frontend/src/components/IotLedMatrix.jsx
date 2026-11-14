import React, { useState, useEffect } from 'react';
import { Cpu, Radio, CheckCircle, AlertTriangle, Sparkles, Activity, Zap, RefreshCw, Power } from 'lucide-react';
import authClient from '../utils/authClient';

// Mapeamento idêntico ao firmware_leds.ino e pose_estimation.py
const LED_DEFINITIONS = [
  { id: 'ombro_dir', label: 'Ombro D.', pin: 2, byte: 'A', x: 88, y: 72, side: 'right' },
  { id: 'ombro_esq', label: 'Ombro E.', pin: 3, byte: 'B', x: 192, y: 72, side: 'left' },
  { id: 'cotovelo_dir', label: 'Cotovelo D.', pin: 4, byte: 'C', x: 62, y: 125, side: 'right' },
  { id: 'cotovelo_esq', label: 'Cotovelo E.', pin: 5, byte: 'D', x: 218, y: 125, side: 'left' },
  { id: 'pulso_dir', label: 'Pulso D.', pin: 6, byte: 'E', x: 42, y: 178, side: 'right' },
  { id: 'pulso_esq', label: 'Pulso E.', pin: 7, byte: 'F', x: 238, y: 178, side: 'left' },
  { id: 'quadril_dir', label: 'Quadril D.', pin: 8, byte: 'G', x: 110, y: 168, side: 'right' },
  { id: 'quadril_esq', label: 'Quadril E.', pin: 9, byte: 'H', x: 170, y: 168, side: 'left' },
  { id: 'joelho_dir', label: 'Joelho D.', pin: 10, byte: 'I', x: 106, y: 235, side: 'right' },
  { id: 'joelho_esq', label: 'Joelho E.', pin: 11, byte: 'J', x: 174, y: 235, side: 'left' },
  { id: 'tornozelo_dir', label: 'Tornozelo D.', pin: 12, byte: 'K', x: 102, y: 295, side: 'right' },
  { id: 'tornozelo_esq', label: 'Tornozelo E.', pin: 13, byte: 'L', x: 178, y: 295, side: 'left' },
];

export function IotLedMatrix({ failedJoints = [], isConnected = false, compact = false }) {
  const [selectedJoint, setSelectedJoint] = useState(null);
  const [hwStatus, setHwStatus] = useState({ is_connected: false, port: 'COM4', active_joints: [] });
  const [isOperating, setIsOperating] = useState(false);

  // Consulta o status real da porta Serial do Arduino periodicamente
  useEffect(() => {
    let unmounted = false;
    const fetchIotStatus = async () => {
      try {
        const res = await fetch('/api/iot/status');
        if (res.ok) {
          const data = await res.json();
          if (!unmounted) setHwStatus(data);
        }
      } catch {}
    };

    fetchIotStatus();
    const interval = setInterval(fetchIotStatus, 3000);
    return () => {
      unmounted = true;
      clearInterval(interval);
    };
  }, []);

  // Mescla falhas da telemetria com acionamentos manuais
  const activeSet = new Set([...(failedJoints || []), ...(hwStatus.active_joints || [])]);
  const isAnyLedActive = activeSet.size > 0;

  // Dispara acendimento ou desligamento individual do LED no Arduino
  const handleToggleLed = async (led) => {
    setIsOperating(true);
    try {
      const res = await authClient.fetchWithAuth('/api/iot/leds/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ byte: led.byte, action: 'toggle' })
      });
      if (res.ok) {
        const updated = await res.json();
        setHwStatus(updated);
      }
    } catch (e) {
      console.warn('Erro ao controlar LED do Arduino:', e);
    } finally {
      setIsOperating(false);
    }
  };

  // Executa teste de bancada varrendo os 12 atuadores
  const handleSweepTest = async () => {
    setIsOperating(true);
    try {
      await authClient.fetchWithAuth('/api/iot/leds/sweep', { method: 'POST' });
    } catch (e) {
      console.warn('Erro ao disparar varredura:', e);
    } finally {
      setIsOperating(false);
    }
  };

  // Apaga todos os LEDs e devolve o controle à IA
  const handleResetLeds = async () => {
    setIsOperating(true);
    try {
      const res = await authClient.fetchWithAuth('/api/iot/leds/reset', { method: 'POST' });
      if (res.ok) {
        const updated = await res.json();
        setHwStatus(updated);
      }
    } catch (e) {
      console.warn('Erro ao resetar LEDs:', e);
    } finally {
      setIsOperating(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
      
      {/* Header do Painel */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={18} color="#f59e0b" />
          <h3 style={{ fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#f8fafc', margin: 0 }}>
            Colete IoT - Controle de Atuadores
          </h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className={`badge ${hwStatus.is_connected ? 'badge-green' : 'badge-amber'}`} style={{ fontSize: '0.65rem' }}>
            {hwStatus.is_connected ? `● Arduino ${hwStatus.port} Conectado` : '● Simulação Virtual'}
          </span>
        </div>
      </div>

      {/* Barra de Ações Rápidas (Varredura e Reset Geral) */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <button
          onClick={handleSweepTest}
          disabled={isOperating}
          className="btn btn-secondary"
          style={{ flex: 1, padding: '6px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px' }}
          title="Aciona sequencialmente os 12 LEDs para teste físico de bancada"
        >
          <Zap size={13} color="#f59e0b" />
          <span>Testar Varredura</span>
        </button>

        <button
          onClick={handleResetLeds}
          disabled={isOperating}
          className="btn btn-secondary"
          style={{ flex: 1, padding: '6px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px', borderColor: 'rgba(239, 68, 68, 0.3)' }}
          title="Envia comando 'R' para apagar todos os LEDs físicos"
        >
          <RefreshCw size={13} color="#f87171" />
          <span>Apagar Todos ('R')</span>
        </button>
      </div>

      <p style={{ fontSize: '0.74rem', color: '#94a3b8', margin: 0 }}>
        Clique em qualquer articulação do corpo virtual para ligar ou desligar o LED físico correspondente no Arduino.
      </p>

      {/* ÁREA CENTRAL: CORPO ANATÔMICO COM OS 12 LEDS */}
      <div style={{
        position: 'relative',
        width: '100%',
        height: compact ? '440px' : '350px',
        background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.7) 0%, rgba(2, 6, 23, 0.9) 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        
        {/* SVG do Corpo Humano Estilizado */}
        <svg
          viewBox="0 0 280 340"
          style={{ width: '100%', height: '100%', maxHeight: '340px' }}
        >
          <defs>
            <filter id="neon-glow-red" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#ef4444" floodOpacity="0.9" />
              <feDropShadow dx="0" dy="0" stdDeviation="8" floodColor="#dc2626" floodOpacity="0.6" />
            </filter>
            
            <filter id="neon-glow-green" x="-30%" y="-30%" width="160%" height="160%">
              <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor="#10b981" floodOpacity="0.5" />
            </filter>
          </defs>

          {/* Silhueta Anatômica: Linhas Conectivas / Esqueleto */}
          <g stroke="rgba(100, 116, 139, 0.4)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="140" cy="32" r="15" fill="rgba(30, 41, 59, 0.8)" stroke="#38bdf8" strokeWidth="2" />
            <line x1="140" y1="47" x2="140" y2="72" />
            <line x1="140" y1="72" x2="140" y2="168" strokeDasharray="3,3" />
            <line x1="88" y1="72" x2="192" y2="72" />
            <line x1="88" y1="72" x2="62" y2="125" />
            <line x1="62" y1="125" x2="42" y2="178" />
            <line x1="192" y1="72" x2="218" y2="125" />
            <line x1="218" y1="125" x2="238" y2="178" />
            <line x1="110" y1="168" x2="170" y2="168" />
            <line x1="110" y1="168" x2="106" y2="235" />
            <line x1="106" y1="235" x2="102" y2="295" />
            <line x1="170" y1="168" x2="174" y2="235" />
            <line x1="174" y1="235" x2="178" y2="295" />
          </g>

          {/* Renderização dos 12 LEDs Interativos */}
          {LED_DEFINITIONS.map((led) => {
            const isActive = activeSet.has(led.id);

            return (
              <g 
                key={led.id} 
                style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                onClick={() => handleToggleLed(led)}
              >
                {/* Halo pulsante quando ativo */}
                {isActive && (
                  <circle
                    cx={led.x}
                    cy={led.y}
                    r="14"
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="2"
                    opacity="0.8"
                    style={{
                      animation: 'pulse 1s infinite alternate'
                    }}
                  />
                )}

                {/* Corpo do LED */}
                <circle
                  cx={led.x}
                  cy={led.y}
                  r={isActive ? "8" : "6"}
                  fill={isActive ? "#ef4444" : "#0f766e"}
                  stroke={isActive ? "#ffffff" : "#14b8a6"}
                  strokeWidth={isActive ? "2" : "1.5"}
                  filter={isActive ? "url(#neon-glow-red)" : "url(#neon-glow-green)"}
                />

                {/* Letra do Protocolo Serial no LED */}
                <text
                  x={led.x}
                  y={led.y + (isActive ? 3 : 2.5)}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize={isActive ? "9" : "7.5"}
                  fontWeight="bold"
                  fontFamily="monospace"
                >
                  {led.byte}
                </text>

                {/* Rótulo da Articulação */}
                <text
                  x={led.side === 'right' ? led.x - 12 : led.x + 12}
                  y={led.y + 3}
                  textAnchor={led.side === 'right' ? 'end' : 'start'}
                  fill={isActive ? '#f87171' : '#94a3b8'}
                  fontSize="7.5"
                  fontWeight={isActive ? "700" : "500"}
                  fontFamily="sans-serif"
                >
                  {led.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Indicador de Status Flutuante */}
        <div style={{
          position: 'absolute',
          bottom: '10px',
          left: '12px',
          right: '12px',
          background: isAnyLedActive ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.2)',
          border: `1px solid ${isAnyLedActive ? '#ef4444' : '#10b981'}`,
          borderRadius: '8px',
          padding: '6px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isAnyLedActive ? (
              <AlertTriangle size={14} color="#ef4444" />
            ) : (
              <CheckCircle size={14} color="#10b981" />
            )}
            <span style={{ fontSize: '0.72rem', fontWeight: '700', color: isAnyLedActive ? '#fca5a5' : '#6ee7b7' }}>
              {isAnyLedActive 
                ? `LEDs Ativos: ${LED_DEFINITIONS.filter(l => activeSet.has(l.id)).map(l => `${l.label} [${l.byte}]`).join(', ')}`
                : 'Trajetória Correta: Todos os 12 LEDs apagados'}
            </span>
          </div>

          <span style={{ fontSize: '0.65rem', color: '#cbd5e1', fontFamily: 'monospace' }}>
            {isAnyLedActive ? 'Buzzer / Sinal Ativo' : 'Reset [Byte R]'}
          </span>
        </div>

      </div>

      {/* Lista Compacta de Portas Digitais Interativas */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: compact ? 'repeat(3, 1fr)' : 'repeat(6, 1fr)',
        gap: '6px'
      }}>
        {LED_DEFINITIONS.map(led => {
          const isActive = activeSet.has(led.id);
          return (
            <button
              key={led.id}
              onClick={() => handleToggleLed(led)}
              style={{
                background: isActive ? 'rgba(239, 68, 68, 0.2)' : 'rgba(15, 23, 42, 0.5)',
                border: `1px solid ${isActive ? '#ef4444' : 'rgba(255, 255, 255, 0.08)'}`,
                borderRadius: '6px',
                padding: '5px 6px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ fontSize: '0.68rem', fontWeight: '700', color: isActive ? '#f87171' : '#38bdf8' }}>
                '{led.byte}' P{led.pin}
              </div>
              <div style={{ fontSize: '0.58rem', color: isActive ? '#fca5a5' : '#94a3b8', whiteSpace: 'nowrap' }}>
                {led.label}
              </div>
            </button>
          );
        })}
      </div>

    </div>
  );
}

export default IotLedMatrix;
