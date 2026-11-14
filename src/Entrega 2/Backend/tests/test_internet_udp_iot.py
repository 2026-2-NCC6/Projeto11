import os
import sys
import json
import time
import unittest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import auth
from serial_manager import arduino_controller, JOINT_TO_BYTE, BYTE_TO_JOINT
import server
from server import app

class TestInternetUdpIot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_auth_credentials_and_jwt(self):
        # 1. Credenciais inválidas
        self.assertFalse(auth.verify_credentials("admin", "senha_errada"))
        self.assertTrue(auth.verify_credentials("admin", "tennis2026"))

        # 2. Emissão e decodificação de token JWT
        token = auth.create_access_token({"sub": "admin"})
        self.assertIsNotNone(token)
        payload = auth.decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("sub"), "admin")

    def test_02_auth_endpoints(self):
        # 1. Tentativa de login com senha incorreta
        res_fail = self.client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        self.assertEqual(res_fail.status_code, 401)

        # 2. Login correto
        res_ok = self.client.post("/api/auth/login", json={"username": "admin", "password": "tennis2026"})
        self.assertEqual(res_ok.status_code, 200)
        data = res_ok.json()
        self.assertIn("access_token", data)
        self.assertEqual(data.get("username"), "admin")

        token = data["access_token"]

        # 3. Verificação com token válido via Header Bearer
        res_verify = self.client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_verify.status_code, 200)
        self.assertEqual(res_verify.json().get("user"), "admin")

        # 4. Verificação com token via Query param (?token=)
        res_query = self.client.get(f"/api/auth/verify?token={token}")
        self.assertEqual(res_query.status_code, 200)

    def test_03_iot_arduino_controller(self):
        # 1. Status inicial
        status = arduino_controller.get_status()
        self.assertIn("is_connected", status)
        self.assertIn("port", status)

        # 2. Acionamento manual de LED individual ('C' = Cotovelo Direito)
        res_c = arduino_controller.trigger_led('C', True)
        self.assertIn('C', res_c.get("active_bytes", []))
        self.assertIn('cotovelo_dir', res_c.get("active_joints", []))

        # 3. Acionamento de um segundo LED ('A' = Ombro Direito)
        res_a = arduino_controller.trigger_led('ombro_dir', True)
        self.assertIn('A', res_a.get("active_bytes", []))
        self.assertIn('C', res_a.get("active_bytes", []))

        # 4. Desligamento individual de 'C' (Ombro 'A' deve permanecer ativo)
        res_off_c = arduino_controller.trigger_led('C', False)
        self.assertNotIn('C', res_off_c.get("active_bytes", []))
        self.assertIn('A', res_off_c.get("active_bytes", []))

        # 5. Reset geral
        res_reset = arduino_controller.reset_all_leds()
        self.assertEqual(len(res_reset.get("active_bytes", [])), 0)

    def test_04_iot_api_endpoints(self):
        # Limpa cookies da sessão do TestClient para testar acesso não autorizado
        self.client.cookies.clear()

        # Status IoT público
        res_status = self.client.get("/api/iot/status")
        self.assertEqual(res_status.status_code, 200)

        # Controle sem autenticação deve retornar 401
        res_unauth = self.client.post("/api/iot/leds/control", json={"byte": "C", "action": "toggle"})
        self.assertEqual(res_unauth.status_code, 401)

        # Obtém token
        res_login = self.client.post("/api/auth/login", json={"username": "admin", "password": "tennis2026"})
        token = res_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Controle com token autenticado
        res_ctrl = self.client.post("/api/iot/leds/control", json={"byte": "C", "action": "toggle"}, headers=headers)
        self.assertEqual(res_ctrl.status_code, 200)
        self.assertIn('C', res_ctrl.json().get("active_bytes", []))

        # Reset via API
        res_rst = self.client.post("/api/iot/leds/reset", headers=headers)
        self.assertEqual(res_rst.status_code, 200)
        self.assertEqual(len(res_rst.json().get("active_bytes", [])), 0)

    def test_05_webrtc_endpoints(self):
        # Servidores ICE públicos
        res_ice = self.client.get("/api/webrtc/ice_servers")
        self.assertEqual(res_ice.status_code, 200)
        self.assertIn("iceServers", res_ice.json())

        # Status geral do serviço
        res_svc = self.client.get("/api/status")
        self.assertEqual(res_svc.status_code, 200)
        self.assertEqual(res_svc.json().get("status"), "online")

if __name__ == "__main__":
    unittest.main()
