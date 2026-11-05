import React from 'react';
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

export default function App() {
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

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '20px 24px 40px 24px' }}>
      
      {/* Barra de Navegação e Controles */}
      <Navbar
        isConnected={isConnected}
        isDemoMode={isDemoMode}
        sessionActive={sessionActive}
        sessionSeconds={sessionSeconds}
        lateralidade={lateralidade}
        audioEnabled={audioEnabled}
        onToggleSession={toggleSession}
        onResetSession={resetSession}
        onToggleHandedness={toggleHandedness}
        onToggleAudio={toggleAudio}
      />

      {/* Grid Principal do Dashboard */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, 1fr)',
        gap: '24px',
        marginBottom: '24px'
      }}>
        
        {/* Coluna Esquerda: Feed de Vídeo + Replay do Último Golpe + Telemetria de Ângulos (7 colunas) */}
        <div style={{ gridColumn: 'span 7', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Feed de Vídeo ao Vivo */}
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
          />

          {/* Replay dos Últimos 5 Segundos do Golpe com MediaPipe */}
          <ReplayCard
            latestReplayUrl={latestReplayUrl}
            telemetry={telemetry}
          />

          {/* Ângulos Articulares 3D */}
          <AngleTelemetry
            angles={telemetry.angles}
            currentStroke={telemetry.stroke_name}
          />

        </div>

        {/* Coluna Direita: IA & Diagnóstico + Painel Físico IoT + Estatísticas (5 colunas) */}
        <div style={{ gridColumn: 'span 5', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Card de Gamificação: Modo Rally Virtual */}
          <RallyGameCard
            gameState={gameState}
            onResetRally={resetRallyGame}
          />

          {/* HUD de Postura e Classificação do Modelo */}
          <PostureHUD
            strokeName={telemetry.stroke_name}
            confidence={telemetry.confidence}
            feedback={telemetry.feedback}
            failedJoints={telemetry.failed_joints}
          />

          {/* Painel IoT dos 12 LEDs do Arduino */}
          <IotLedMatrix
            failedJoints={telemetry.failed_joints}
            isConnected={isConnected}
          />

          {/* Estatísticas Acumuladas */}
          <PerformanceStats
            stats={stats}
          />

        </div>

      </div>

      {/* Seção Inferior: Histórico Completo de Golpes */}
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
