import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

class TestSDGsGameAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.env_patch = patch.dict(os.environ, {"TURSO_DATABASE_URL": "", "TURSO_AUTH_TOKEN": "", "VERCEL": "", "SDGS_ADMIN_PASSWORD": ""})
        cls.env_patch.start()
        cls.db_patch = patch("app.database.DB_PATH", Path(cls.temp.name) / "test.db")
        cls.db_patch.start()
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)
        cls.db_patch.stop()
        cls.env_patch.stop()
        cls.temp.cleanup()

    def test_01_goals(self):
        res = self.client.get("/api/game/goals")
        self.assertEqual(res.status_code, 200)
        goals = res.json()
        self.assertEqual(len(goals), 17)
        self.assertEqual(goals[0]["name"], "消除貧窮")
        self.assertEqual(goals[12]["name"], "氣候行動")

    def test_02_targets(self):
        res = self.client.get("/api/game/targets")
        self.assertEqual(res.status_code, 200)
        targets = res.json()
        self.assertEqual(len(targets), 169)

    def test_03_game_flow(self):
        start_payload = {
            "nickname": "永續小英雄",
            "organization": "師大附中",
            "avatar": "🌱",
            "mode": "standard",
            "question_count": 5
        }
        res_start = self.client.post("/api/game/start", json=start_payload)
        self.assertEqual(res_start.status_code, 200)
        data = res_start.json()
        session_id = data["session_id"]
        questions = data["questions"]
        self.assertEqual(len(questions), 5)

        q1 = questions[0]
        ans_payload = {
            "session_id": session_id,
            "question_index": 0,
            "target_id": q1["target_id"],
            "selected_goal_id": q1["correct_goal_id"],
            "correct_goal_id": q1["correct_goal_id"],
            "time_spent_ms": 1200,
            "current_combo": 0
        }
        res_ans = self.client.post("/api/game/answer", json=ans_payload)
        self.assertEqual(res_ans.status_code, 200)
        ans_data = res_ans.json()
        self.assertTrue(ans_data["is_correct"])
        self.assertEqual(ans_data["new_combo"], 1)

        finish_payload = {
            "session_id": session_id,
            "total_score": 600,
            "total_questions": 5,
            "correct_count": 5,
            "combo_max": 5,
            "time_taken_seconds": 20.0
        }
        res_finish = self.client.post("/api/game/finish", json=finish_payload)
        self.assertEqual(res_finish.status_code, 200)
        fin_data = res_finish.json()
        self.assertEqual(fin_data["status"], "success")

        res_lb = self.client.get("/api/game/leaderboard")
        self.assertEqual(res_lb.status_code, 200)
        lb = res_lb.json()
        self.assertGreaterEqual(len(lb), 1)

    def test_04_admin_flow(self):
        login_payload = {
            "username": "admin",
            "password": "sdgs2030admin"
        }
        res_login = self.client.post("/api/admin/login", json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        res_stats = self.client.get("/api/admin/stats", headers=headers)
        self.assertEqual(res_stats.status_code, 200)

        res_rec = self.client.get("/api/admin/records", headers=headers)
        self.assertEqual(res_rec.status_code, 200)

        res_targets = self.client.get("/api/admin/targets?goal_id=13", headers=headers)
        self.assertEqual(res_targets.status_code, 200)
        self.assertEqual(len(res_targets.json()), 5)

if __name__ == "__main__":
    unittest.main()
