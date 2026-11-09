import os
import sys
import unittest
import numpy as np

# Adicionar Backend ao sys.path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import rule_engine
from gamification_engine import GamificationEngine
from hud_renderer import TennisHUD

class DummyLandmark:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

def create_mock_landmarks(elbow_angle_deg=140, knee_angle_deg=120):
    """
    Gera 33 landmarks sintéticos para teste com os ângulos articulares desejados.
    """
    landmarks = [DummyLandmark() for _ in range(33)]
    
    rad_elbow = np.radians(elbow_angle_deg)
    # Vértice cotovelo em (0, 0, 0)
    # Ombro em (0, 1, 0) -> vetor cotovelo->ombro = (0, 1, 0)
    # Pulso em (sin(rad), cos(rad), 0) -> vetor cotovelo->pulso tem ângulo rad_elbow com ombro
    landmarks[14] = DummyLandmark(0.0, 0.0, 0.0) # Cotovelo D
    landmarks[12] = DummyLandmark(0.0, 1.0, 0.0) # Ombro D
    landmarks[16] = DummyLandmark(float(np.sin(rad_elbow)), float(np.cos(rad_elbow)), 0.0) # Pulso D

    # Braço Esquerdo
    landmarks[13] = DummyLandmark(0.0, 0.0, 0.0) # Cotovelo E
    landmarks[11] = DummyLandmark(0.0, 1.0, 0.0) # Ombro E
    landmarks[15] = DummyLandmark(float(np.sin(rad_elbow)), float(np.cos(rad_elbow)), 0.0) # Pulso E

    # Joelhos (24: Quadril, 26: Joelho, 28: Tornozelo)
    rad_knee = np.radians(knee_angle_deg)
    landmarks[26] = DummyLandmark(0.0, 0.0, 0.0)
    landmarks[24] = DummyLandmark(0.0, 1.0, 0.0)
    landmarks[28] = DummyLandmark(float(np.sin(rad_knee)), float(np.cos(rad_knee)), 0.0)

    landmarks[25] = DummyLandmark(0.0, 0.0, 0.0)
    landmarks[23] = DummyLandmark(0.0, 1.0, 0.0)
    landmarks[27] = DummyLandmark(float(np.sin(rad_knee)), float(np.cos(rad_knee)), 0.0)

    return landmarks

class TestRuleEngineGamification(unittest.TestCase):
    def test_forehand_perfect(self):
        lm = create_mock_landmarks(elbow_angle_deg=145)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(0, lm, 'destro')
        self.assertEqual(grade, "PERFECT")
        self.assertEqual(score, 1.0)
        self.assertEqual(len(failed), 0)
        self.assertTrue("extensão" in feedback.lower() or "extensao" in feedback.lower())

    def test_forehand_good(self):
        lm = create_mock_landmarks(elbow_angle_deg=125)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(0, lm, 'destro')
        self.assertEqual(grade, "GOOD")
        self.assertEqual(score, 0.85)
        self.assertEqual(len(failed), 0)

    def test_forehand_fault(self):
        lm = create_mock_landmarks(elbow_angle_deg=95)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(0, lm, 'destro')
        self.assertEqual(grade, "FAULT")
        self.assertEqual(score, 0.0)
        self.assertIn("cotovelo_dir", failed)

    def test_backhand_and_saque(self):
        # Backhand perfeito (140 graus cotovelo não dominante)
        lm_bh = create_mock_landmarks(elbow_angle_deg=140)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(1, lm_bh, 'destro')
        self.assertEqual(grade, "PERFECT")
        self.assertEqual(score, 1.0)
        self.assertEqual(len(failed), 0)

        # Saque com boa impulsão (120 graus joelhos)
        lm_serve = create_mock_landmarks(knee_angle_deg=120, elbow_angle_deg=150)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(2, lm_serve, 'destro')
        self.assertEqual(grade, "PERFECT")
        self.assertEqual(score, 1.0)
        self.assertEqual(len(failed), 0)

        # Saque com flexão pobre (> 150 graus)
        lm_serve_bad = create_mock_landmarks(knee_angle_deg=165)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(2, lm_serve_bad, 'destro')
        self.assertEqual(grade, "FAULT")
        self.assertIn("joelho_dir", failed)

    def test_canhoto_lateralidade(self):
        lm = create_mock_landmarks(elbow_angle_deg=90)
        feedback, angles, failed, score, grade = rule_engine.evaluate_stroke(0, lm, 'canhoto')
        self.assertEqual(grade, "FAULT")
        self.assertIn("cotovelo_esq", failed)


class TestGamificationEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.join(TEST_DIR, "temp_data")
        self.engine = GamificationEngine(max_lives=3, data_dir=self.temp_dir)
        self.engine.reset_session()

    def tearDown(self):
        # Limpar arquivos temporários se criados
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initial_state(self):
        telemetry = self.engine.get_telemetry()
        self.assertEqual(telemetry["lives"], 3)
        self.assertEqual(telemetry["score"], 0)
        self.assertEqual(telemetry["rally_count"], 0)
        self.assertEqual(telemetry["combo_multiplier"], 1.0)
        self.assertFalse(telemetry["is_game_over"])
        self.assertEqual(telemetry["level"], 1)

    def test_successful_stroke_and_combo(self):
        # 1 golpe Forehand perfeito
        self.engine.record_stroke(
            stroke_id=0,
            stroke_name="Forehand",
            confidence=0.95,
            failed_joints=[],
            angles={"elbow_r": 145},
            quality_score=1.0,
            grade="PERFECT"
        )
        self.assertEqual(self.engine.rally_count, 1)
        self.assertEqual(self.engine.score, 100) # Base 100 * 1.0 * 1.0
        self.assertEqual(self.engine.combo_streak, 1)
        self.assertEqual(self.engine.lives, 3)

        # 2º golpe Backhand perfeito
        self.engine.record_stroke(
            stroke_id=1,
            stroke_name="Backhand",
            confidence=0.92,
            failed_joints=[],
            angles={"elbow_l": 140},
            quality_score=1.0,
            grade="PERFECT"
        )
        self.assertEqual(self.engine.rally_count, 2)
        self.assertEqual(self.engine.score, 220) # 100 + (120 * 1.0)

        # 3º golpe atinge combo 1.5x
        self.engine.record_stroke(
            stroke_id=0,
            stroke_name="Forehand",
            confidence=0.90,
            failed_joints=[],
            angles={"elbow_r": 145},
            quality_score=1.0,
            grade="PERFECT"
        )
        self.assertEqual(self.engine.combo_multiplier, 1.5)
        # 220 + (100 * 1.0 * 1.5) = 220 + 150 = 370
        self.assertEqual(self.engine.score, 370)

    def test_faulty_stroke_breaks_combo_without_losing_life(self):
        # Primeiro faz 3 golpes bons para ter combo 1.5x
        for _ in range(3):
            self.engine.record_stroke(0, "Forehand", 0.9, [], {}, 1.0, "PERFECT")
        self.assertEqual(self.engine.combo_multiplier, 1.5)
        self.assertEqual(self.engine.lives, 3)

        # Golpe com ajuste biomecânico: quebra combo, mas NÃO desconta vida (vida só é perdida se errar a bola)
        self.engine.record_stroke(0, "Forehand", 0.88, ["cotovelo_dir"], {}, 0.5, "FAULT")
        self.assertEqual(self.engine.lives, 3) # Vidas mantidas intactas!
        self.assertEqual(self.engine.combo_streak, 0)
        self.assertEqual(self.engine.combo_multiplier, 1.0)
        self.assertGreater(self.engine.rally_count, 3) # Rally continua!

    def test_game_over_and_reset(self):
        # Perde vidas por bolas perdidas consecutivas (quando erra a bola)
        self.engine.lives = 0
        self.engine.is_game_over = True

        self.assertEqual(self.engine.lives, 0)
        self.assertTrue(self.engine.is_game_over)

        # Tentar registrar novo golpe enquanto em Game Over não surte efeito
        prev_score = self.engine.score
        self.engine.record_stroke(0, "Forehand", 0.95, [], {}, 1.0, "PERFECT")
        self.assertEqual(self.engine.score, prev_score)

        # Reiniciar Rally
        self.engine.reset_rally()
        self.assertEqual(self.engine.lives, 3)
        self.assertFalse(self.engine.is_game_over)
        self.assertEqual(self.engine.rally_count, 0)

    def test_level_up_and_export(self):
        # Acumula XP executando saques perfeitos (150 pts * combo)
        for _ in range(8):
            self.engine.record_stroke(2, "Saque", 0.95, [], {}, 1.0, "PERFECT")

        self.assertGreaterEqual(self.engine.xp, 500)
        self.assertGreaterEqual(self.engine.level, 2)
        self.assertEqual(self.engine.rank_title, "Amador")
        self.assertIn("SUBINDO_DE_NIVEL", self.engine.unlocked_achievements)

        # Testa exportação de sessão
        export_file = os.path.join(self.temp_dir, "custom_export.json")
        res = self.engine.export_session_history(export_file)
        self.assertTrue(os.path.exists(export_file))

        import json
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("session_summary", data)
            self.assertIn("events", data)
            self.assertEqual(data["session_summary"]["level"], self.engine.level)
            self.assertEqual(len(data["events"]), 8)

    def test_achievements_unlock(self):
        # 5 acertos seguidos devem desbloquear a conquista PRIMEIRO_RALLY
        for _ in range(5):
            self.engine.record_stroke(0, "Forehand", 0.95, [], {}, 1.0, "PERFECT")

        self.assertIn("PRIMEIRO_RALLY", self.engine.unlocked_achievements)
        self.assertIn("PERFEICAO", self.engine.unlocked_achievements)
        self.assertIn("COMBO_3X", self.engine.unlocked_achievements)


class TestHUDRenderer(unittest.TestCase):
    def test_render_smoke_test(self):
        hud = TennisHUD()
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        game_state = {
            "mode": "RALLY",
            "score": 450,
            "lives": 3,
            "max_lives": 3,
            "rally_count": 5,
            "best_rally": 8,
            "combo_streak": 4,
            "combo_multiplier": 1.5,
            "is_game_over": False,
            "level": 2,
            "rank_title": "Amador",
            "xp_progress": 45.0,
            "last_grade": "PERFECT",
            "last_points": 150,
            "last_feedback": "Excelente Forehand! (+150 pts)",
            "last_stroke_name": "Forehand",
            "new_achievement": None
        }

        output_frame = hud.render(dummy_frame, game_state, fps=30)
        self.assertIsNotNone(output_frame)
        self.assertEqual(output_frame.shape, (480, 640, 3))

    def test_render_game_over(self):
        hud = TennisHUD()
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        game_state = {
            "mode": "RALLY",
            "score": 1200,
            "lives": 0,
            "max_lives": 3,
            "is_game_over": True,
            "best_rally": 12,
            "total_strokes": 20,
            "accuracy": 85.0
        }

        output_frame = hud.render(dummy_frame, game_state, fps=30)
        self.assertIsNotNone(output_frame)

if __name__ == '__main__':
    unittest.main()
