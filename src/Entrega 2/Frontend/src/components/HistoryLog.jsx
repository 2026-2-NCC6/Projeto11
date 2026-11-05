import React, { useState } from 'react';
import { History, CheckCircle2, AlertTriangle, Download, Trash2, Filter } from 'lucide-react';

export function HistoryLog({ history = [], onClearHistory }) {
  const [filter, setFilter] = useState('all'); // 'all', 'approved', 'correction'

  const filteredHistory = history.filter(item => {
    if (filter === 'approved') return item.status === 'approved';
    if (filter === 'correction') return item.status === 'correction';
    return true;
  });

  const exportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(history, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `tennissync-sessao-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Cabeçalho */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <History size={18} color="#8b5cf6" />
          <span style={{ fontSize: '0.8rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
            Registro Histórico de Golpes na Sessão ({filteredHistory.length})
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Filtros */}
          <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-surface-elevated)', padding: '2px', borderRadius: '8px' }}>
            <button
              onClick={() => setFilter('all')}
              className={`btn btn-secondary ${filter === 'all' ? 'active' : ''}`}
              style={{ padding: '4px 8px', fontSize: '0.7rem' }}
            >
              Todos
            </button>
            <button
              onClick={() => setFilter('approved')}
              className={`btn btn-secondary ${filter === 'approved' ? 'active' : ''}`}
              style={{ padding: '4px 8px', fontSize: '0.7rem' }}
            >
              Aprovados
            </button>
            <button
              onClick={() => setFilter('correction')}
              className={`btn btn-secondary ${filter === 'correction' ? 'active' : ''}`}
              style={{ padding: '4px 8px', fontSize: '0.7rem' }}
            >
              Correções
            </button>
          </div>

          {/* Exportar */}
          {history.length > 0 && (
            <button
              onClick={exportJSON}
              className="btn btn-secondary"
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              title="Exportar dados da sessão em JSON"
            >
              <Download size={13} />
              <span>Exportar</span>
            </button>
          )}
        </div>
      </div>

      {/* Lista com Scroll */}
      <div style={{ maxHeight: '280px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filteredHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '30px', color: '#64748b', fontSize: '0.85rem' }}>
            Nenhum golpe registrado ainda nesta sessão. Realize um golpe em frente à câmera para disparar a IA.
          </div>
        ) : (
          filteredHistory.map((item) => (
            <div
              key={item.id}
              style={{
                background: 'var(--bg-surface-elevated)',
                border: `1px solid ${item.status === 'approved' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.25)'}`,
                borderRadius: '8px',
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {item.status === 'approved' ? (
                  <CheckCircle2 size={16} color="#10b981" />
                ) : (
                  <AlertTriangle size={16} color="#ef4444" />
                )}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <strong style={{ fontSize: '0.85rem', color: '#f8fafc' }}>{item.stroke}</strong>
                    <span className="badge badge-slate" style={{ fontSize: '0.65rem' }}>
                      {item.confidence}% Conf.
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#64748b', fontFamily: 'var(--font-mono)' }}>
                      {item.timestamp}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: item.status === 'approved' ? '#94a3b8' : '#fca5a5', marginTop: '2px' }}>
                    {item.feedback}
                  </div>
                </div>
              </div>

              {/* Juntas com desvio */}
              {item.failed_joints && item.failed_joints.length > 0 && (
                <div style={{ display: 'flex', gap: '4px' }}>
                  {item.failed_joints.map(j => (
                    <span key={j} className="badge badge-red" style={{ fontSize: '0.6rem', padding: '2px 6px' }}>
                      {j.replace('_', ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

    </div>
  );
}
