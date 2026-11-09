import unittest
import time
from Backend.gamification_engine import GamificationEngine

class TestBallGamification(unittest.TestCase):
    def setUp(self):
        # Inicializa a engine com 3 vidas em modo limpo
        self.engine = GamificationEngine(max_lives=3)
        self.engine.reset_session()
        self.engine.spawn_next_ball(now=100.0)

    def test_spawn_ball(self):
        self.assertEqual(self.engine.ball_status, 'APPROACHING')
        self.assertEqual(self.engine.ball_id, 1)
        self.assertIn(self.engine.target_stroke_name, ['Forehand', 'Backhand', 'Saque'])
        self.assertGreater(self.engine.flight_duration, 0)
        self.assertEqual(self.engine.spawn_time, 100.0)

    def test_early_hit_no_life_loss(self):
        """Golpear antes da janela de impacto (< 0.75) NÃO deve descontar vida do jogador."""
        # flight_duration ~ 2.8s. 100.0 + 1.0s = progress 0.35 (< 0.75)
        early_time = 101.0
        
        initial_lives = self.engine.lives
        stroke_id = self.engine.target_stroke_id
        stroke_name = self.engine.target_stroke_name

        orig_time = time.time
        try:
            time.time = lambda: early_time
            result = self.engine.record_stroke(
                stroke_id=stroke_id,
                stroke_name=stroke_name,
                confidence=0.90,
                failed_joints=[],
                angles={},
                quality_score=95.0,
                grade="PERFECT"
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["timing"], "TOO_EARLY")
            # A vida NÃO é descontada por movimento antecipado
            self.assertEqual(self.engine.lives, initial_lives)
            self.assertIn("Aguarde a bola chegar", result["feedback"])
        finally:
            time.time = orig_time

    def test_hit_in_window(self):
        """Golpear dentro da janela (0.75 a 1.05) com postura válida resulta em HIT e pontuação."""
        # 100.0 + 2.8 * 0.85 = 102.38s
        hit_time = 100.0 + (self.engine.flight_duration * 0.85)

        orig_time = time.time
        try:
            time.time = lambda: hit_time
            stroke_id = self.engine.target_stroke_id
            stroke_name = self.engine.target_stroke_name

            result = self.engine.record_stroke(
                stroke_id=stroke_id,
                stroke_name=stroke_name,
                confidence=0.92,
                failed_joints=[],
                angles={},
                quality_score=100.0,
                grade="PERFECT"
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["grade"], "PERFECT")
            self.assertEqual(self.engine.ball_status, "HIT")
            self.assertEqual(self.engine.rally_count, 1)
            self.assertEqual(self.engine.combo_streak, 1)
            self.assertGreater(self.engine.score, 0)
            self.assertGreater(self.engine.xp, 0)
        finally:
            time.time = orig_time

    def test_too_late_miss_loses_life(self):
        """Se o jogador erra a bola (bola ultrapassa o tempo > 1.05 sem rebatida), perde 1 vida."""
        late_time = 100.0 + (self.engine.flight_duration * 1.10)

        initial_lives = self.engine.lives
        self.engine.update_ball_state(now=late_time)

        self.assertEqual(self.engine.ball_status, "TOO_LATE")
        # Aqui SIM desconta vida, pois errou a bola
        self.assertEqual(self.engine.lives, initial_lives - 1)
        self.assertEqual(self.engine.combo_streak, 0)

    def test_different_stroke_rebounds_without_losing_life(self):
        """Executar golpe diferente do sugerido rebate a bola sem perda de vida."""
        mid_time = 100.0 + (self.engine.flight_duration * 0.85)

        orig_time = time.time
        try:
            time.time = lambda: mid_time
            wrong_stroke_id = 1 if self.engine.target_stroke_id == 0 else 0
            wrong_name = "Backhand" if wrong_stroke_id == 1 else "Forehand"

            initial_lives = self.engine.lives
            result = self.engine.record_stroke(
                stroke_id=wrong_stroke_id,
                stroke_name=wrong_name,
                confidence=0.90,
                failed_joints=[],
                angles={},
                quality_score=90.0,
                grade="GOOD"
            )
            self.assertIsNotNone(result)
            self.assertEqual(self.engine.ball_status, "HIT")
            self.assertEqual(self.engine.lives, initial_lives)
            self.assertEqual(self.engine.rally_count, 1)
        finally:
            time.time = orig_time

    def test_game_over(self):
        """Perder 3 vidas consecutivas por errar bolas consecutivas aciona Game Over."""
        self.engine.lives = 1
        late_time = 100.0 + (self.engine.flight_duration * 1.15)
        self.engine.update_ball_state(now=late_time)

        self.assertEqual(self.engine.lives, 0)
        self.assertTrue(self.engine.is_game_over)

    def test_no_ghost_ball_life_loss_when_auto_spawn_false(self):
        """Com auto_spawn=False (padrão de produção), vidas não são perdidas no vácuo."""
        engine = GamificationEngine(max_lives=3, auto_spawn=False)
        self.assertEqual(engine.lives, 3)
        # Simula 10 segundos chamando get_telemetry
        for t in range(10):
            telemetry = engine.get_telemetry(now=100.0 + t)
            self.assertEqual(telemetry["lives"], 3)
            self.assertEqual(engine.lives, 3)

if __name__ == '__main__':
    unittest.main()
