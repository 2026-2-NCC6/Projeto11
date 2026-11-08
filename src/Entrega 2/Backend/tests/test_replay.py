import os
import sys
import unittest
import numpy as np
import cv2

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(TEST_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pose_estimation import create_compatible_videowriter

class TestReplayVideoWriter(unittest.TestCase):
    def test_compatible_videowriter_generates_valid_h264(self):
        temp_video = os.path.join(TEST_DIR, "test_output_replay.mp4")
        if os.path.exists(temp_video):
            os.remove(temp_video)

        writer = create_compatible_videowriter(temp_video, fps=25.0, width=640, height=480)
        self.assertIsNotNone(writer, "VideoWriter não deve ser nulo")
        self.assertTrue(writer.isOpened(), "VideoWriter deve estar aberto com sucesso")

        # Escrever 15 frames sintéticos
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Desenha uma linha simulando landmarks
        cv2.line(dummy_frame, (100, 100), (300, 300), (0, 255, 0), 3)

        for _ in range(15):
            writer.write(dummy_frame)
        writer.release()

        self.assertTrue(os.path.exists(temp_video), "O arquivo .mp4 deve existir")
        self.assertGreater(os.path.getsize(temp_video), 500, "O tamanho do arquivo deve ser maior que 500 bytes")

        # Verificar se o FourCC é legível e compatível
        cap = cv2.VideoCapture(temp_video)
        self.assertTrue(cap.isOpened(), "O vídeo gerado deve poder ser aberto")
        code = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = ''.join([chr((code >> 8 * i) & 0xFF) for i in range(4)])
        self.assertIn(fourcc_str.lower(), ['h264', 'avc1', 'mp4v'], f"FourCC inesperado: {fourcc_str}")
        self.assertEqual(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), 15)
        cap.release()

        # Limpar
        if os.path.exists(temp_video):
            os.remove(temp_video)

if __name__ == '__main__':
    unittest.main()
