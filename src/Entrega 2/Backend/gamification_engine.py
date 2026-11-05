import os
import json
import time

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
    def __init__(self, max_lives=3, data_dir=None):
        self.max_lives = max_lives
        self.lives = max_lives
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

    def record_stroke(self, stroke_id, stroke_name, confidence, failed_joints, angles, quality_score, grade):
        """
        Processa um golpe avaliado pela Camada de Diagnóstico.
        Atualiza o estado de Rally, vidas, combo e pontuação.
        """
        if stroke_id not in [0, 1, 2]:
            return None

        # Se já estiver em Game Over, ignora pontuação até reiniciar
        if self.is_game_over:
            return None

        now = time.time()
        self.total_strokes += 1
        self.stroke_counts[stroke_name] = self.stroke_counts.get(stroke_name, 0) + 1

        is_success = (len(failed_joints) == 0 and grade in ["PERFECT", "GOOD"])

        base_points_map = {0: 100, 1: 120, 2: 150} # Forehand=100, Backhand=120, Saque=150
        base_points = base_points_map.get(stroke_id, 100)

        points_awarded = 0

        if is_success:
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

            feedback_text = f"Excelente {stroke_name}! (+{points_awarded} pts)"
        else:
            # Falha biomecânica: quebra de combo e perda de vida
            self.faulty_strokes += 1
            self.perfect_streak = 0
            self.combo_streak = 0
            self.combo_multiplier = 1.0
            self.lives = max(0, self.lives - 1)

            fault_reason = ", ".join(failed_joints) if failed_joints else "Postura incorreta"
            feedback_text = f"Falha no {stroke_name} ({fault_reason}) -1 Vida!"

            if self.lives <= 0:
                self.is_game_over = True
                self.game_over_time = now

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

    def get_telemetry(self):
        """Retorna estado completo serializável para WebSocket e HUD."""
        min_xp, max_xp, progress_percent = self.get_xp_bounds()

        # Verifica se o aviso de conquista já expirou (5 segundos)
        active_achievement = None
        if self.new_achievement and (time.time() - self.new_achievement_time < 5.0):
            active_achievement = self.new_achievement

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
            "new_achievement": active_achievement
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
