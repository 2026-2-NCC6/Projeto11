import os
import sys
import unittest
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pose_estimation import MAPA_LEDS
import rule_engine

class TestAuditAndTrajectory(unittest.TestCase):

    def test_mapa_leds_alignment(self):
        """Verifica se o dicionário de LEDs está 100% alinhado com o firmware do Arduino."""
        expected = {
            "ombro_dir": b'A', "ombro_esq": b'B',
            "cotovelo_dir": b'C', "cotovelo_esq": b'D',
            "pulso_dir": b'E', "pulso_esq": b'F',
            "quadril_dir": b'G', "quadril_esq": b'H',
            "joelho_dir": b'I', "joelho_esq": b'J',
            "tornozelo_dir": b'K', "tornozelo_esq": b'L'
        }
        for joint, byte_val in expected.items():
            self.assertEqual(MAPA_LEDS.get(joint), byte_val, f"Erro no mapeamento do LED para {joint}")

    def test_trajectory_evaluation_stroke(self):
        """Verifica se a avaliação de trajetória contínua analisa sequências temporais de landmarks."""
        # Cria 30 frames de landmarks sintéticos simulando preparação e impacto
        fake_trajectory = []
        for i in range(30):
            frame_lm = []
            for j in range(33):
                # Mock Landmark object com x, y, z, visibility
                class FakeLM:
                    def __init__(self, x, y, z):
                        self.x = x
                        self.y = y
                        self.z = z
                        self.visibility = 0.95
                frame_lm.append(FakeLM(0.5, 0.5, 0.0))
            
            # Articulações relevantes para destro:
            # 12: Ombro dir, 14: Cotovelo dir, 16: Pulso dir
            # 11: Ombro esq, 23: Quadril esq, 24: Quadril dir
            # Ângulo de ~150 graus (Forehand estendido correto)
            frame_lm[12] = FakeLM(0.4, 0.4, 0.0)
            frame_lm[14] = FakeLM(0.6, 0.5, 0.0)
            frame_lm[16] = FakeLM(0.8, 0.55, 0.0)
            
            # Joelho dir: 24 (quadril), 26 (joelho), 28 (tornozelo) ~160 graus
            frame_lm[24] = FakeLM(0.45, 0.65, 0.0)
            frame_lm[26] = FakeLM(0.45, 0.80, 0.0)
            frame_lm[28] = FakeLM(0.45, 0.95, 0.0)

            fake_trajectory.append(frame_lm)

        feedback, angles, failed, score, grade, worst_frame = rule_engine.evaluate_stroke_trajectory(
            0, fake_trajectory, lateralidade="destro"
        )

        self.assertIn(grade, ["PERFECT", "GOOD", "FAULT"])
        self.assertIsInstance(score, float)
        self.assertIsInstance(failed, list)
        self.assertIsInstance(feedback, str)
        print(f"\n[Test Biomecânica] Nota: {grade} | Score: {score:.1f} | Falhas: {failed} | Feedback: {feedback}")

    def test_raw_videos_structure(self):
        """Garante que existam estritamente as 4 pastas oficiais no dataset."""
        raw_dir = os.path.join(BASE_DIR, "dataset", "raw_videos")
        categories = [d for d in os.listdir(raw_dir) if os.path.isdir(os.path.join(raw_dir, d))]
        expected_categories = {"forehand", "backhand", "saque", "repouso"}
        self.assertEqual(set(categories), expected_categories, f"Pastas em raw_videos divergentes: {categories}")

if __name__ == "__main__":
    unittest.main()
