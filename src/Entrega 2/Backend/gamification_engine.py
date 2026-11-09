import os
import json
import time
import random

RANKS = [
    (0, "Iniciante", 500),
    (500, "Amador", 1200),
    (1200, "Avançado", 2500),
    (2500, "Semi-Pro", 4500),
    (4500, "Grand Slam Master", 10000)
]

ACHIEVEMENT_DEFINITIONS = {
    "PRIMEIRO_RALLY": {"title": "Primeiro Rally", "desc": "Manteve um rally de 5 golpes válidos", "icon": "🎾"},
    "COMBO_3X": {"title": "Hot Streak!", "desc": "Alcançou multiplicador de combo 2.0x", "icon": "🔥"},
    "COMBO_MASTER": {"title": "Combo Master", "desc": "Alcançou multiplicador máximo 3.0x", "icon": "⚡"},
    "PERFEICAO": {"title": "Perfeição", "desc": "Executou 3 golpes com nota PERFECT consecutivos", "icon": "⭐"},
    "SUBINDO_DE_NIVEL": {"title": "Promovido!", "desc": "Alcançou o Nível 2 (Amador)", "icon": "🏆"},
    "MURALHA": {"title": "Muralha do Fundo", "desc": "Manteve um rally de 15 golpes", "icon": "🛡️"}
}

class GamificationEngine:
    """
    Engine de Gamificação e Modo Rally Virtual do TennisSync.
    Controla o estado do jogo, pontuação dinâmica, multiplicadores de combo,
    vidas do jogador, acúmulo de XP, patentes e persistência de dados.
    """
    def __init__(self, max_lives=3, data_dir=None, auto_spawn=False):
        self.max_lives = max_lives
        self.lives = max_lives
        self.auto_spawn = auto_spawn
        self.score = 0
        self.rally_count = 0
        self.best_rally = 0
        self.combo_streak = 0
        self.combo_multiplier = 1.0
        self.is_game_over = False
        self.game_over_time = 0.0

        # Estatísticas acumuladas da sessão
        self.total_strokes = 0
        self.successful_strokes = 0
        self.faulty_strokes = 0
        self.perfect_streak = 0
        self.stroke_counts = {"Forehand": 0, "Backhand": 0, "Saque": 0}
        self.stroke_success = {"Forehand": 0, "Backhand": 0, "Saque": 0}

        # Feedback do último golpe
        self.last_stroke_id = 3
        self.last_stroke_name = "Repouso"
        self.last_confidence = 0.0
        self.last_grade = "NONE"
        self.last_points = 0
        self.last_feedback = "Pronto para o próximo golpe"
        self.last_failed_joints = []
        self.last_event_time = 0.0

        # Sistema de RPG e Progressão
        self.xp = 0
        self.level = 1
        self.rank_title = "Iniciante"
        self.unlocked_achievements = set()
        self.new_achievement = None
        self.new_achievement_time = 0.0

        # Histórico de eventos da sessão
        self.session_events = []

        # -------------------------------------------------------------
        # Mecânica de Bola Virtual, Alvos e Timing
        # -------------------------------------------------------------
        self.ball_id = 0
        self.target_stroke_id = 0
        self.target_stroke_name = "Forehand"
        self.target_x = 0.72
        self.target_y = 0.68
        self.flight_duration = 2.8
        self.spawn_time = time.time()
        self.ball_status = 'WAITING'  # 'WAITING', 'APPROACHING', 'HIT', 'TOO_EARLY', 'TOO_LATE', 'FAULT_STROKE'
        self.waiting_since = time.time()
        self.last_result_time = 0.0
        self.stroke_sequence = [0, 1, 0, 1, 2] # Ciclo dinâmico de treino
        self.sequence_idx = 0

        # Diretório de persistência
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.profile_path = os.path.join(self.data_dir, "player_profile.json")
        self.load_profile()

    def update_level(self):
        """Calcula o nível e o título com base no XP acumulado."""
        current_rank = RANKS[0]
        level = 1
        for idx, (min_xp, title, max_xp) in enumerate(RANKS, start=1):
            if self.xp >= min_xp:
                current_rank = (min_xp, title, max_xp)
                level = idx
            else:
                break
        self.level = level
        self.rank_title = current_rank[1]

        if self.level >= 2:
            self.unlock_achievement("SUBINDO_DE_NIVEL")

    def get_xp_bounds(self):
        """Retorna (min_xp, max_xp, progresso_percentual) para a barra de XP."""
        idx = min(self.level - 1, len(RANKS) - 1)
        min_xp, _, max_xp = RANKS[idx]
        span = max_xp - min_xp
        current_in_span = max(0, self.xp - min_xp)
        progress = min(100.0, (current_in_span / span * 100.0)) if span > 0 else 100.0
        return min_xp, max_xp, round(progress, 1)

    def calculate_combo_multiplier(self):
        """Determina o multiplicador baseado no número de acertos consecutivos."""
        if self.combo_streak >= 8:
            return 3.0
        elif self.combo_streak >= 5:
            return 2.0
        elif self.combo_streak >= 3:
            return 1.5
        return 1.0

    def prepare_serve(self, now=None):
        """Prepara o jogador para realizar o Saque de abertura ou de reinício após falta."""
        now = now or time.time()
        self.ball_id += 1
        self.target_stroke_id = 2
        self.target_stroke_name = "Saque"
        self.target_x = 0.50
        self.target_y = 0.38
        self.flight_duration = 0.0
        self.spawn_time = now
        self.ball_status = 'NEED_SERVE'
        self.last_feedback = "Execute um SAQUE para colocar a bola em jogo!"

    def spawn_next_ball(self, now=None, force_stroke=None):
        """Lança uma nova bola em direção a uma NOVA POSIÇÃO alternada da quadra."""
        now = now or time.time()
        self.ball_id += 1
        
        # Alterna entre Forehand e Backhand para dinâmica de rally realista
        if force_stroke is not None:
            self.target_stroke_id = force_stroke
        else:
            # Alterna em relação ao último golpe (se foi forehand, vai para backhand e vice-versa)
            if self.target_stroke_id == 0:
                self.target_stroke_id = 1
            else:
                self.target_stroke_id = 0

        stroke_names = {0: "Forehand", 1: "Backhand", 2: "Saque"}
        self.target_stroke_name = stroke_names[self.target_stroke_id]

        import random
        # Variação sutil da nova posição para não ser fixa no mesmo ponto
        if self.target_stroke_id == 0:  # Forehand (quadrante direito)
            positions = [(0.72, 0.68), (0.78, 0.72), (0.68, 0.62)]
            self.target_x, self.target_y = random.choice(positions)
        elif self.target_stroke_id == 1:  # Backhand (quadrante esquerdo)
            positions = [(0.28, 0.68), (0.22, 0.72), (0.32, 0.62)]
            self.target_x, self.target_y = random.choice(positions)
        else:  # Saque (ponto central alto)
            self.target_x = 0.50
            self.target_y = 0.38

        # Velocidade: ligeiramente mais rápida conforme o rally aumenta (2.6s a 1.9s)
        speed_factor = max(0.70, 1.0 - (self.rally_count * 0.02))
        self.flight_duration = round(2.6 * speed_factor, 2)
        self.spawn_time = now
        self.ball_status = 'APPROACHING'

    def update_ball_state(self, now=None):
        """
        Atualiza a máquina de estados temporal da bola a cada frame.
        Detecta bola perdida (TOO_LATE) e gerencia transições automáticas.
        """
        now = now or time.time()

        if self.is_game_over:
            self.ball_status = 'GAME_OVER'
            return

        if self.ball_status == 'WAITING':
            if self.auto_spawn and (now - self.waiting_since) >= 1.5:
                self.spawn_next_ball(now)
            return

        if self.ball_status == 'SERVED':
            # Após o saque arremessar a bola para o outro lado (1.0s), o adversário rebate para uma nova posição
            if (now - self.last_result_time) >= 1.0:
                self.spawn_next_ball(now)
            return

        if self.ball_status in ['HIT', 'TOO_EARLY', 'TOO_LATE', 'FAULT_STROKE']:
            # Mantém a animação de resultado por 1.3s antes de preparar a próxima jogada
            if (now - self.last_result_time) >= 1.3:
                if self.ball_status == 'HIT':
                    # Acerto! O adversário rebate para uma NOVA POSIÇÃO da quadra
                    self.spawn_next_ball(now)
                else:
                    # Erro/Falta cometida: Alterna entre preparar Saque de reinício ou nova bola
                    if random.random() > 0.45:
                        self.prepare_serve(now)
                    else:
                        self.spawn_next_ball(now)
            return

        if self.ball_status == 'APPROACHING':
            progress = (now - self.spawn_time) / self.flight_duration
            if progress > 1.05:
                # Bola passou direto sem o jogador golpear a tempo!
                self.ball_status = 'TOO_LATE'
                self.last_result_time = now
                self.faulty_strokes += 1
                self.total_strokes += 1
                self.perfect_streak = 0
                self.combo_streak = 0
                self.combo_multiplier = 1.0
                self.lives = max(0, self.lives - 1)
                self.last_grade = "FAULT"
                self.last_points = 0
                self.last_feedback = f"Bola perdida! Não golpeou a tempo (-1 Vida)"
                self.last_event_time = now

                if self.lives <= 0:
                    self.is_game_over = True
                    self.game_over_time = now

    def record_stroke(self, stroke_id, stroke_name, confidence, failed_joints, angles, quality_score, grade):
        """
        Processa um golpe avaliado pela Camada de Diagnóstico.
        Atualiza o estado de Rally, vidas, combo e pontuação com validação de timing da bola.
        """
        if stroke_id not in [0, 1, 2]:
            return None

        # Se já estiver em Game Over, ignora pontuação até reiniciar
        if self.is_game_over:
            return None

        now = time.time()
        self.update_ball_state(now)

        # -------------------------------------------------------------
        # Validação de Timing da Bola Virtual e Saque
        # -------------------------------------------------------------
        if self.ball_status == 'NEED_SERVE':
            if stroke_id == 2:  # Saque executado com sucesso
                self.ball_status = 'SERVED'
                self.last_result_time = now
                self.successful_strokes += 1
                self.stroke_success[stroke_name] = self.stroke_success.get(stroke_name, 0) + 1
                self.rally_count = max(1, self.rally_count)
                self.combo_streak = 1
                self.combo_multiplier = 1.0
                self.score += 150
                self.xp += 50
                self.update_level()
                self.last_grade = grade if grade in ["PERFECT", "GOOD"] else "GOOD"
                self.last_points = 150
                self.last_feedback = "Saque potente! Bola arremessada para a quadra adversária!"
                self.last_stroke_name = stroke_name
                self.last_event_time = now
                self.save_profile()
                return {
                    "timestamp": now,
                    "stroke": stroke_name,
                    "confidence": round(confidence, 2),
                    "grade": self.last_grade,
                    "quality_score": 1.0,
                    "points": 150,
                    "combo_multiplier": 1.0,
                    "rally_count": self.rally_count,
                    "lives": self.lives,
                    "timing": "SERVE_HIT",
                    "feedback": self.last_feedback
                }
            else:
                # Se fez outro golpe durante o saque, já lança a bola na nova posição
                self.spawn_next_ball(now, force_stroke=stroke_id)

        if self.ball_status == 'APPROACHING':
            progress = (now - self.spawn_time) / self.flight_duration

            # 1. Movimento ANTES da bola chegar na janela (< 0.75):
            # A vida NÃO é descontada por erro de timing prévio; orienta o jogador e mantém a bola a caminho
            if progress < 0.75:
                self.last_feedback = f"Aguarde a bola chegar na área de rebatida!"
                self.last_stroke_name = stroke_name
                self.last_event_time = now
                self.save_profile()
                return {
                    "timestamp": now,
                    "stroke": stroke_name,
                    "confidence": round(confidence, 2),
                    "grade": "EARLY",
                    "quality_score": round(quality_score, 2),
                    "points": 0,
                    "combo_multiplier": self.combo_multiplier,
                    "rally_count": self.rally_count,
                    "lives": self.lives,
                    "timing": "TOO_EARLY",
                    "feedback": self.last_feedback
                }

        self.total_strokes += 1
        self.stroke_counts[stroke_name] = self.stroke_counts.get(stroke_name, 0) + 1

        is_success = (len(failed_joints) == 0 and grade in ["PERFECT", "GOOD"])

        base_points_map = {0: 100, 1: 120, 2: 150} # Forehand=100, Backhand=120, Saque=150
        base_points = base_points_map.get(stroke_id, 100)

        points_awarded = 0

        if is_success:
            self.ball_status = 'HIT'
            self.last_result_time = now
            self.successful_strokes += 1
            self.stroke_success[stroke_name] = self.stroke_success.get(stroke_name, 0) + 1
            self.rally_count += 1
            if self.rally_count > self.best_rally:
                self.best_rally = self.rally_count

            self.combo_streak += 1
            self.combo_multiplier = self.calculate_combo_multiplier()

            if grade == "PERFECT":
                self.perfect_streak += 1
            else:
                self.perfect_streak = 0

            # Cálculo de pontuação com bônus de qualidade e combo
            points_awarded = int(base_points * quality_score * self.combo_multiplier)
            self.score += points_awarded

            # Ganho de XP proporcional aos pontos
            earned_xp = max(10, int(points_awarded * 0.4))
            self.xp += earned_xp
            self.update_level()

            feedback_text = f"Excelente {stroke_name}! Rebatida perfeita (+{points_awarded} pts)"
        else:
            # Falha técnica ou biomecânica no movimento:
            # A vida NÃO é descontada! (A vida só é perdida quando o jogador erra a bola).
            # A rebatida acontece, pontuando com valor proporcional ao score de qualidade.
            self.ball_status = 'HIT'
            self.last_result_time = now
            self.successful_strokes += 1
            self.stroke_success[stroke_name] = self.stroke_success.get(stroke_name, 0) + 1
            self.rally_count += 1
            if self.rally_count > self.best_rally:
                self.best_rally = self.rally_count

            self.perfect_streak = 0
            self.combo_streak = 0
            self.combo_multiplier = 1.0

            points_awarded = int(base_points * max(0.35, quality_score) * 1.0)
            self.score += points_awarded

            earned_xp = max(5, int(points_awarded * 0.3))
            self.xp += earned_xp
            self.update_level()

            fault_reason = ", ".join(failed_joints) if failed_joints else "Postura imperfeita"
            feedback_text = f"Rebatida no {stroke_name} com ajuste: {fault_reason} (+{points_awarded} pts)"

        # Atualiza feedback instantâneo
        self.last_stroke_id = stroke_id
        self.last_stroke_name = stroke_name
        self.last_confidence = confidence
        self.last_grade = grade
        self.last_points = points_awarded
        self.last_feedback = feedback_text
        self.last_failed_joints = failed_joints
        self.last_event_time = now

        # Verificar conquistas
        self.check_achievements()

        # Salvar evento no histórico da sessão
        event_record = {
            "timestamp": now,
            "stroke": stroke_name,
            "confidence": round(confidence, 2),
            "grade": grade,
            "quality_score": round(quality_score, 2),
            "points": points_awarded,
            "combo_multiplier": self.combo_multiplier,
            "rally_count": self.rally_count,
            "lives": self.lives,
            "failed_joints": failed_joints,
            "angles": angles
        }
        self.session_events.append(event_record)

        # Salva o perfil atualizado
        self.save_profile()

        return event_record

    def check_achievements(self):
        """Avalia regras para desbloqueio de insígnias."""
        if self.rally_count >= 5:
            self.unlock_achievement("PRIMEIRO_RALLY")
        if self.rally_count >= 15:
            self.unlock_achievement("MURALHA")
        if self.combo_multiplier >= 2.0:
            self.unlock_achievement("COMBO_3X")
        if self.combo_multiplier >= 3.0:
            self.unlock_achievement("COMBO_MASTER")
        if self.perfect_streak >= 3:
            self.unlock_achievement("PERFEICAO")

    def unlock_achievement(self, code):
        """Desbloqueia uma conquista e registra notificação temporária."""
        if code in ACHIEVEMENT_DEFINITIONS and code not in self.unlocked_achievements:
            self.unlocked_achievements.add(code)
            self.new_achievement = {
                "code": code,
                "title": ACHIEVEMENT_DEFINITIONS[code]["title"],
                "desc": ACHIEVEMENT_DEFINITIONS[code]["desc"],
                "icon": ACHIEVEMENT_DEFINITIONS[code]["icon"]
            }
            self.new_achievement_time = time.time()

    def reset_rally(self):
        """Reinicia uma nova partida de Rally (mantendo XP e conquistas acumuladas)."""
        self.lives = self.max_lives
        self.rally_count = 0
        self.combo_streak = 0
        self.combo_multiplier = 1.0
        self.is_game_over = False
        self.score = 0
        self.last_grade = "NONE"
        self.last_points = 0
        self.last_feedback = "Novo Rally iniciado! Boa sorte!"
        self.last_event_time = time.time()
        self.ball_status = 'WAITING'
        self.waiting_since = time.time()

    def reset_session(self):
        """Reinicia todas as métricas da sessão atual."""
        self.reset_rally()
        self.total_strokes = 0
        self.successful_strokes = 0
        self.faulty_strokes = 0
        self.stroke_counts = {"Forehand": 0, "Backhand": 0, "Saque": 0}
        self.stroke_success = {"Forehand": 0, "Backhand": 0, "Saque": 0}
        self.session_events = []

    def get_accuracy(self):
        """Retorna a taxa percentual de acertos biomecânicos."""
        if self.total_strokes == 0:
            return 100.0
        return round((self.successful_strokes / self.total_strokes) * 100.0, 1)

    def get_telemetry(self, now=None):
        """Retorna estado completo serializável para WebSocket e HUD."""
        now = now or time.time()
        self.update_ball_state(now)

        min_xp, max_xp, progress_percent = self.get_xp_bounds()

        # Verifica se o aviso de conquista já expirou (5 segundos)
        active_achievement = None
        if self.new_achievement and (time.time() - self.new_achievement_time < 5.0):
            active_achievement = self.new_achievement

        # Cálculo de progresso e timing da bola
        ball_progress = 0.0
        time_remaining = 0.0
        if self.ball_status == 'APPROACHING' and self.flight_duration > 0:
            ball_progress = min(1.1, (now - self.spawn_time) / self.flight_duration)
            time_remaining = max(0.0, (1.0 - ball_progress) * self.flight_duration)
        elif self.ball_status == 'HIT':
            ball_progress = 1.0

        return {
            "mode": "RALLY",
            "score": self.score,
            "lives": self.lives,
            "max_lives": self.max_lives,
            "rally_count": self.rally_count,
            "best_rally": self.best_rally,
            "combo_streak": self.combo_streak,
            "combo_multiplier": self.combo_multiplier,
            "is_game_over": self.is_game_over,
            "accuracy": self.get_accuracy(),
            "total_strokes": self.total_strokes,
            "successful_strokes": self.successful_strokes,
            "faulty_strokes": self.faulty_strokes,
            "last_grade": self.last_grade,
            "last_points": self.last_points,
            "last_feedback": self.last_feedback,
            "last_stroke_name": self.last_stroke_name,
            "last_failed_joints": self.last_failed_joints,
            "xp": self.xp,
            "level": self.level,
            "rank_title": self.rank_title,
            "xp_min": min_xp,
            "xp_next": max_xp,
            "xp_progress": progress_percent,
            "unlocked_achievements": list(self.unlocked_achievements),
            "new_achievement": active_achievement,
            "ball_challenge": {
                "active": not self.is_game_over,
                "ball_id": self.ball_id,
                "target_stroke_id": self.target_stroke_id,
                "target_stroke_name": self.target_stroke_name,
                "target_x": self.target_x,
                "target_y": self.target_y,
                "flight_duration": self.flight_duration,
                "progress": round(ball_progress, 3),
                "time_remaining": round(time_remaining, 2),
                "status": self.ball_status,
                "hit_window_active": 0.75 <= ball_progress <= 1.05 and self.ball_status == 'APPROACHING',
                "is_early": ball_progress < 0.75 and self.ball_status == 'APPROACHING'
            }
        }

    def save_profile(self):
        """Salva perfil e progresso do jogador em JSON."""
        data = {
            "xp": self.xp,
            "level": self.level,
            "rank_title": self.rank_title,
            "best_rally": self.best_rally,
            "total_strokes": self.total_strokes,
            "successful_strokes": self.successful_strokes,
            "unlocked_achievements": list(self.unlocked_achievements),
            "last_updated": time.time()
        }
        try:
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[GamificationEngine] Erro ao salvar perfil: {e}")

    def load_profile(self):
        """Carrega perfil e progresso do jogador se existir."""
        if not os.path.exists(self.profile_path):
            return
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.xp = data.get("xp", 0)
                self.best_rally = data.get("best_rally", 0)
                self.unlocked_achievements = set(data.get("unlocked_achievements", []))
                self.update_level()
        except Exception as e:
            print(f"[GamificationEngine] Erro ao carregar perfil: {e}")

    def export_session_history(self, filepath=None):
        """Exporta histórico completo da sessão para consumo do Frontend."""
        target_path = filepath or os.path.join(self.data_dir, "session_history.json")
        payload = {
            "session_summary": {
                "score": self.score,
                "best_rally": self.best_rally,
                "total_strokes": self.total_strokes,
                "accuracy": self.get_accuracy(),
                "rank_title": self.rank_title,
                "level": self.level,
                "xp": self.xp
            },
            "events": self.session_events
        }
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return target_path
        except Exception as e:
            print(f"[GamificationEngine] Erro ao exportar sessão: {e}")
            return None
