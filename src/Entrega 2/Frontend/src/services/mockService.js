/**
 * Fallback de conexão para TenniSync quando o servidor backend está offline.
 * NUNCA gera golpes simulados, falsos positivos ou instruções sonoras artificiais.
 * Mantém o sistema em estado de espera neutro até que o backend real conecte.
 */

export function createMockStream(onUpdate) {
  let timer = null;

  const tick = () => {
    const telemetry = {
      timestamp: Date.now(),
      fps: 0,
      stroke_id: 3,
      stroke_name: 'Repouso',
      confidence: 0.0,
      feedback: 'Desconectado do servidor. Inicie: py -3.11 server.py',
      failed_joints: [],
      angles: {
        elbow_r: 120,
        elbow_l: 120,
        knee_r: 160,
        knee_l: 160,
        shoulder_r: 90,
        shoulder_l: 90
      },
      led_active: false,
      active_leds: [],
      lateralidade: 'destro',
      athlete_detected: false,
      is_dark: false,
      event_id: 0,
      latest_replay_url: null,
      latest_replay_filename: null,
      game: {
        mode: "RALLY",
        score: 0,
        lives: 3,
        max_lives: 3,
        rally_count: 0,
        best_rally: 0,
        combo_streak: 0,
        combo_multiplier: 1.0,
        is_game_over: false,
        accuracy: 100.0,
        total_strokes: 0,
        successful_strokes: 0,
        faulty_strokes: 0,
        last_grade: "NONE",
        last_points: 0,
        last_feedback: "Aguardando conexão real com a câmera",
        last_stroke_name: "Repouso",
        last_failed_joints: [],
        xp: 0,
        level: 1,
        rank_title: "Iniciante",
        xp_min: 0,
        xp_next: 500,
        xp_progress: 0.0,
        unlocked_achievements: [],
        new_achievement: null
      }
    };

    onUpdate(telemetry);
  };

  timer = setInterval(tick, 2000);
  tick();

  return () => {
    if (timer) clearInterval(timer);
  };
}
