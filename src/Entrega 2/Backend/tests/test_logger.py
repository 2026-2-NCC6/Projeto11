# Backend/tests/test_logger.py
import unittest
import os
import time
from Backend.logger import (
    log_debug, log_info, log_warn, log_error, log_exception, log_sampled,
    set_level, get_recent_logs, clear_logs, LOG_FILE
)

class TestTenniSyncLogger(unittest.TestCase):
    def setUp(self):
        clear_logs()
        set_level("DEBUG")

    def test_log_levels_and_ring_buffer(self):
        log_info("SYSTEM", "Teste de inicialização", {"status": "ok"})
        log_warn("GAME-API", "Aviso de teste", {"score": 10})
        log_error("ERROR", "Erro de teste", {"code": 500})

        logs = get_recent_logs(limit=10)
        self.assertGreaterEqual(len(logs), 3)

        tags = [item["tag"] for item in logs]
        self.assertIn("SYSTEM", tags)
        self.assertIn("GAME-API", tags)
        self.assertIn("ERROR", tags)

    def test_filter_by_tag_and_level(self):
        log_debug("CAM/STREAM", "Frame lido", {"fps": 30})
        log_info("POSE-AI", "Atleta detectado", {"conf": 0.95})
        log_warn("POSE-AI", "Atleta ocluso", {"consec": 5})

        pose_logs = get_recent_logs(tag="POSE-AI")
        self.assertEqual(len(pose_logs), 2)

        warn_logs = get_recent_logs(min_level="WARN")
        self.assertTrue(all(item["level"] in ["WARN", "ERROR"] for item in warn_logs))

    def test_log_sampled(self):
        # Primeira chamada deve disparar
        first = log_sampled("test_fps", 1.0, "CAM/STREAM", "FPS 30")
        self.assertTrue(first)

        # Segunda chamada imediata deve ser bloqueada
        second = log_sampled("test_fps", 1.0, "CAM/STREAM", "FPS 30")
        self.assertFalse(second)

    def test_log_exception(self):
        try:
            raise ValueError("Exceção simulada para teste")
        except Exception as exc:
            log_exception("GAME-API", "Falha de processamento", exc, {"user_id": 42})

        logs = get_recent_logs(tag="GAME-API")
        self.assertEqual(len(logs), 1)
        err = logs[0]
        self.assertEqual(err["level"], "ERROR")
        self.assertIn("ValueError", err["message"])
        self.assertIn("traceback", err["extra"])
        self.assertEqual(err["extra"]["user_id"], 42)

    def test_file_persistence(self):
        log_info("SYSTEM", "Persistência em arquivo testada")
        self.assertTrue(os.path.exists(LOG_FILE))
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Persistência em arquivo testada", content)

if __name__ == "__main__":
    unittest.main()
