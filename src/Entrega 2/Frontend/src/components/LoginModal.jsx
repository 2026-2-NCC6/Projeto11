import React, { useState } from 'react';
import { Lock, User, ShieldCheck, Video, Cpu, ArrowRight, AlertCircle, Key } from 'lucide-react';
import authClient from '../utils/authClient';

export function LoginModal({ onLoginSuccess }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await authClient.login(username, password);
      if (onLoginSuccess) {
        onLoginSuccess(data);
      }
    } catch (err) {
      setError(err.message || 'Falha ao autenticar.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(2, 6, 23, 0.88)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '16px'
    }}>
      <div style={{
        maxWidth: '440px',
        width: '100%',
        backgroundColor: '#0f172a',
        borderRadius: '16px',
        border: '1px solid rgba(56, 189, 248, 0.25)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 30px rgba(56, 189, 248, 0.1)',
        overflow: 'hidden',
        color: '#f8fafc'
      }}>
        {/* Header com Gradiente */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(16, 185, 129, 0.15) 100%)',
          padding: '24px 24px 20px 24px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          textAlign: 'center'
        }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '12px',
            backgroundColor: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '12px'
          }}>
            <ShieldCheck size={28} color="#38bdf8" />
          </div>
          <h2 style={{ margin: '0 0 6px 0', fontSize: '1.25rem', fontWeight: '700', letterSpacing: '-0.02em' }}>
            TenniSync • Acesso Remoto
          </h2>
          <p style={{ margin: 0, fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.4 }}>
            Streaming de Vídeo UDP • IA Biomecânica • Controle IoT
          </p>
        </div>

        {/* Formulário */}
        <form onSubmit={handleSubmit} style={{ padding: '24px' }}>
          {error && (
            <div style={{
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              color: '#f87171',
              fontSize: '0.82rem',
              marginBottom: '18px'
            }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '6px', fontWeight: '500' }}>
              Usuário
            </label>
            <div style={{ position: 'relative' }}>
              <User size={16} color="#64748b" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  backgroundColor: '#1e293b',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  padding: '10px 12px 10px 36px',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none'
                }}
                placeholder="admin"
              />
            </div>
          </div>

          <div style={{ marginBottom: '22px' }}>
            <label style={{ display: 'block', fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '6px', fontWeight: '500' }}>
              Senha de Acesso
            </label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} color="#64748b" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  backgroundColor: '#1e293b',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '8px',
                  padding: '10px 12px 10px 36px',
                  color: '#ffffff',
                  fontSize: '0.88rem',
                  outline: 'none'
                }}
                placeholder="••••••••"
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.72rem', color: '#64748b' }}>
              <span>Padrão: <code style={{ color: '#38bdf8' }}>admin</code> / <code style={{ color: '#38bdf8' }}>tennis2026</code></span>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              backgroundColor: '#10b981',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '12px',
              fontSize: '0.9rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
              opacity: loading ? 0.7 : 1,
              transition: 'background-color 0.2s'
            }}
          >
            {loading ? (
              <span>Autenticando...</span>
            ) : (
              <>
                <span>Entrar e Ativar Câmera UDP</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Rodapé Informativo */}
        <div style={{
          backgroundColor: '#090d16',
          padding: '14px 20px',
          borderTop: '1px solid rgba(255, 255, 255, 0.05)',
          display: 'flex',
          justifyContent: 'space-around',
          fontSize: '0.72rem',
          color: '#94a3b8'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Video size={13} color="#10b981" />
            <span>UDP WebRTC</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={13} color="#f59e0b" />
            <span>Arduino Uno (COM4)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Key size={13} color="#38bdf8" />
            <span>JWT Bearer</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginModal;
