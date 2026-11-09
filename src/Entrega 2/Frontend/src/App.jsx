import React, { useState } from 'react';
import { useTennisSync } from './hooks/useTennisSync';
import { Navbar } from './components/Navbar';
import { VideoFeed } from './components/VideoFeed';
import { ReplayCard } from './components/ReplayCard';
import { PostureHUD } from './components/PostureHUD';
import { AngleTelemetry } from './components/AngleTelemetry';
import { IotLedMatrix } from './components/IotLedMatrix';
import { PerformanceStats } from './components/PerformanceStats';
import { HistoryLog } from './components/HistoryLog';
import { RallyGameCard } from './components/RallyGameCard';
import logger from './utils/logger';

class DiagnosticErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    logger.error('RUNTIME-ERROR', `Falha de renderização React capturada pelo ErrorBoundary: ${error?.message || error}`, {
      stack: error?.stack,
      componentStack: errorInfo?.componentStack
    });
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          backgroundColor: '#090d16',
          color: '#f8fafc',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px',
          fontFamily: 'Inter, system-ui, sans-serif'
        }}>
          <div style={{
            maxWidth: '680px',
            width: '100%',
            backgroundColor: '#1e293b',
            border: '1px solid #ef4444',
            borderRadius: '16px',
            padding: '28px',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
          }}>
            <h2 style={{ color: '#ef4444', margin: '0 0 12px 0', fontSize: '1.3rem', display: 'flex', alignItems: 'center', gap: '10px' }}>
              ⚠️ Erro de Renderização Interceptado (TenniSync Diagnostic)
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '0.92rem', marginBottom: '16px', lineHeight: 1.5 }}>
              O sistema de diagnóstico capturou um erro não tratado na interface. O stack trace completo e as variáveis de telemetria foram registrados no console e no buffer em memória (<code style={{ color: '#38bdf8' }}>window.TenniSyncLogger.dump()</code>).
            </p>
            <pre style={{
              backgroundColor: '#0f172a',
              color: '#f87171',
              padding: '14px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              overflowX: 'auto',
              maxHeight: '200px',
              whiteSpace: 'pre-wrap'
            }}>
              {this.state.error?.toString()}
              {this.state.errorInfo?.componentStack}
            </pre>
            <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
              <button
                onClick={this.handleReset}
                style={{
                  backgroundColor: '#0284c7',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '10px 18px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                Tentar Novamente
              </button>
              <button
                onClick={this.handleReload}
                style={{
                  backgroundColor: '#475569',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '10px 18px',
                  fontWeight: '500',
                  cursor: 'pointer'
                }}
              >
                Recarregar Página
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function MainDashboard() {
  const {
    isConnected,
    isDemoMode,
    sessionActive,
    sessionSeconds,
    lateralidade,
    audioEnabled,
    telemetry,
    latestReplayUrl,
    gameState,
    history,
    stats,
    handleTelemetryUpdate,
    toggleSession,
    resetSession,
    toggleHandedness,
    toggleAudio,
    resetRallyGame
  } = useTennisSync();

  // Modos de layout: 'fullscreen' (câmera cheia), 'split_iot' (3/4 câmera + 1/4 IoT), 'dashboard' (clássico)
  const [viewMode, setViewMode] = useState('split_iot');

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '20px 24px 40px 24px' }}>
      
      {/* Barra de Navegação com Seletor de Visões e Controles */}
      <Navbar
        isConnected={isConnected}
        isDemoMode={isDemoMode}
        sessionActive={sessionActive}
        sessionSeconds={sessionSeconds}
        lateralidade={lateralidade}
        audioEnabled={audioEnabled}
        viewMode={viewMode}
        onChangeViewMode={setViewMode}
        onToggleSession={toggleSession}
        onResetSession={resetSession}
        onToggleHandedness={toggleHandedness}
        onToggleAudio={toggleAudio}
      />

      {/* ============================================================== */}
      {/* MODO 1: CÂMERA CHEIA (FULLSCREEN) COM JOGO VIRTUAL & COMPLEMENTOS */}
      {/* ============================================================== */}
      {viewMode === 'fullscreen' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '24px' }}>
          
          {/* Câmera e Jogo Virtual Ocupando Todo o Topo da Tela */}
          <VideoFeed
            isConnected={isConnected}
            isDemoMode={isDemoMode}
            fps={telemetry.fps}
            currentStroke={telemetry.stroke_name}
            feedback={telemetry.feedback}
            failedJoints={telemetry.failed_joints}
            athleteDetected={telemetry.athlete_detected}
            isDark={telemetry.is_dark}
            telemetry={telemetry}
            onTelemetryUpdate={handleTelemetryUpdate}
            gameState={gameState}
            onResetGame={resetRallyGame}
            containerHeight="580px"
          />

          {/* Complementos Dispostos na Parte Inferior da Tela */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: '20px'
          }}>
            {/* Card de Gamificação & Vidas (span 3) */}
            <div style={{ gridColumn: 'span 3' }}>
              <RallyGameCard
                gameState={gameState}
                onResetRally={resetRallyGame}
              />
            </div>

            {/* Replay dos Últimos 5 Segundos (span 3) */}
            <div style={{ gridColumn: 'span 3' }}>
              <ReplayCard
                latestReplayUrl={latestReplayUrl}
                telemetry={telemetry}
              />
            </div>

            {/* Ângulos Articulares 3D (span 3) */}
            <div style={{ gridColumn: 'span 3' }}>
              <AngleTelemetry
                angles={telemetry.angles}
                currentStroke={telemetry.stroke_name}
              />
            </div>

            {/* Boneco IoT Anatômico Compacto (span 3) */}
            <div style={{ gridColumn: 'span 3' }}>
              <IotLedMatrix
                failedJoints={telemetry.failed_joints}
                isConnected={isConnected}
                compact={true}
              />
            </div>
          </div>

          {/* Linha Adicional: Estatísticas e HUD de Postura */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: '20px'
          }}>
            <div style={{ gridColumn: 'span 6' }}>
              <PostureHUD
                strokeName={telemetry.stroke_name}
                confidence={telemetry.confidence}
                feedback={telemetry.feedback}
                failedJoints={telemetry.failed_joints}
              />
            </div>
            <div style={{ gridColumn: 'span 6' }}>
              <PerformanceStats stats={stats} />
            </div>
          </div>

        </div>
      )}

      {/* ============================================================== */}
      {/* MODO 2: DIVISÃO 3/4 CÂMERA (75%) E 1/4 BONECO IOT (25%) À DIREITA */}
      {/* ============================================================== */}
      {viewMode === 'split_iot' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '24px' }}>
          
          {/* Grid Principal Superior: 9 Colunas (75%) Câmera / 3 Colunas (25%) IoT */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: '24px'
          }}>
            {/* 3/4 da Tela: Câmera + Jogo Virtual com Alvo, Sombra e Bola */}
            <div style={{ gridColumn: 'span 9' }}>
              <VideoFeed
                isConnected={isConnected}
                isDemoMode={isDemoMode}
                fps={telemetry.fps}
                currentStroke={telemetry.stroke_name}
                feedback={telemetry.feedback}
                failedJoints={telemetry.failed_joints}
                athleteDetected={telemetry.athlete_detected}
                isDark={telemetry.is_dark}
                telemetry={telemetry}
                onTelemetryUpdate={handleTelemetryUpdate}
                gameState={gameState}
                onResetGame={resetRallyGame}
                containerHeight="520px"
              />
            </div>

            {/* 1/4 da Tela à Direita: Boneco IoT com 12 Atuadores */}
            <div style={{ gridColumn: 'span 3', display: 'flex', flexDirection: 'column' }}>
              <IotLedMatrix
                failedJoints={telemetry.failed_joints}
                isConnected={isConnected}
                compact={true}
              />
            </div>
          </div>

          {/* Grid Inferior: Complementos de Análise e Gamificação */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: '24px'
          }}>
            <div style={{ gridColumn: 'span 4' }}>
              <RallyGameCard
                gameState={gameState}
                onResetRally={resetRallyGame}
              />
            </div>

            <div style={{ gridColumn: 'span 4' }}>
              <ReplayCard
                latestReplayUrl={latestReplayUrl}
                telemetry={telemetry}
              />
            </div>

            <div style={{ gridColumn: 'span 4' }}>
              <AngleTelemetry
                angles={telemetry.angles}
                currentStroke={telemetry.stroke_name}
              />
            </div>
          </div>

          {/* HUD de Postura e Estatísticas */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: '24px'
          }}>
            <div style={{ gridColumn: 'span 6' }}>
              <PostureHUD
                strokeName={telemetry.stroke_name}
                confidence={telemetry.confidence}
                feedback={telemetry.feedback}
                failedJoints={telemetry.failed_joints}
              />
            </div>
            <div style={{ gridColumn: 'span 6' }}>
              <PerformanceStats stats={stats} />
            </div>
          </div>

        </div>
      )}

      {/* ============================================================== */}
      {/* MODO 3: PAINEL ANALÍTICO CLÁSSICO (7 COLUNAS / 5 COLUNAS)      */}
      {/* ============================================================== */}
      {viewMode === 'dashboard' && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, 1fr)',
          gap: '24px',
          marginBottom: '24px'
        }}>
          {/* Coluna Esquerda: Vídeo + Replay + Ângulos (7 colunas) */}
          <div style={{ gridColumn: 'span 7', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <VideoFeed
              isConnected={isConnected}
              isDemoMode={isDemoMode}
              fps={telemetry.fps}
              currentStroke={telemetry.stroke_name}
              feedback={telemetry.feedback}
              failedJoints={telemetry.failed_joints}
              athleteDetected={telemetry.athlete_detected}
              isDark={telemetry.is_dark}
              telemetry={telemetry}
              onTelemetryUpdate={handleTelemetryUpdate}
              gameState={gameState}
              onResetGame={resetRallyGame}
            />

            <ReplayCard
              latestReplayUrl={latestReplayUrl}
              telemetry={telemetry}
            />

            <AngleTelemetry
              angles={telemetry.angles}
              currentStroke={telemetry.stroke_name}
            />
          </div>

          {/* Coluna Direita: Modo Rally + Postura + IoT + Stats (5 colunas) */}
          <div style={{ gridColumn: 'span 5', display: 'flex', flexDirection: 'column', gap: '24px' }}>
            <RallyGameCard
              gameState={gameState}
              onResetRally={resetRallyGame}
            />

            <PostureHUD
              strokeName={telemetry.stroke_name}
              confidence={telemetry.confidence}
              feedback={telemetry.feedback}
              failedJoints={telemetry.failed_joints}
            />

            <IotLedMatrix
              failedJoints={telemetry.failed_joints}
              isConnected={isConnected}
            />

            <PerformanceStats
              stats={stats}
            />
          </div>
        </div>
      )}

      {/* Seção Inferior Universal: Histórico Completo de Golpes */}
      <HistoryLog
        history={history}
        onClearHistory={resetSession}
      />

      {/* Rodapé institucional */}
      <footer style={{
        marginTop: '32px',
        textAlign: 'center',
        fontSize: '0.75rem',
        color: '#64748b',
        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        paddingTop: '20px'
      }}>
        TenniSync • Entrega 2 • Projeto Interdisciplinar • Engenharia da Computação FECAP 2026/1
      </footer>

    </div>
  );
}

export default function App() {
  return (
    <DiagnosticErrorBoundary>
      <MainDashboard />
    </DiagnosticErrorBoundary>
  );
}
