import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db_connection
from app.auth import verify_admin_token


class AnnualMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'TURSO_DATABASE_URL':'','TURSO_AUTH_TOKEN':'','VERCEL':''})
        self.env.start()
        self.db=patch('app.database.DB_PATH',Path(self.temp.name)/'game.db');self.db.start()
        self.context=TestClient(app);self.client=self.context.__enter__()
        app.dependency_overrides[verify_admin_token]=lambda:{'username':'admin','role':'admin'}
        self.registry=patch('app.academic_years.urllib.request.urlopen',side_effect=lambda *args,**kw:io.BytesIO(json.dumps([{'id':1},{'id':2}]).encode()))
        self.registry.start()
        result=self.client.post('/api/admin/academic-years/initialize',json={'id':2,'source_id':1})
        self.assertEqual(result.status_code,200,result.text)

    def tearDown(self):
        self.registry.stop();app.dependency_overrides.clear();self.context.__exit__(None,None,None)
        self.db.stop();self.env.stop();self.temp.cleanup()

    def test_material_copy_and_game_records_are_independent(self):
        header={'X-Academic-Year':'2'}
        self.assertEqual(len(self.client.get('/api/game/goals',headers=header).json()),17)
        self.assertEqual(len(self.client.get('/api/game/targets',headers=header).json()),169)
        self.assertEqual(self.client.get('/api/game/leaderboard',headers=header).json(),[])
        result=self.client.post('/api/game/start',headers=header,json={'nickname':'2027 學員','mode':'standard','question_count':5})
        self.assertEqual(result.status_code,200,result.text)
        question=result.json()['questions'][0]
        answer=self.client.post('/api/game/answer',headers=header,json={'session_id':result.json()['session_id'],'question_index':0,'target_id':question['target_id'],'selected_goal_id':question['correct_goal_id'],'correct_goal_id':question['correct_goal_id']})
        self.assertEqual(answer.status_code,200,answer.text)
        conn=get_db_connection(unscoped=True)
        try:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM game_sessions').fetchone()[0],0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM ay2_game_sessions').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM ay2_game_details').fetchone()[0],1)
        finally:conn.close()

    def test_other_or_invalid_year_cannot_fall_back_to_2026(self):
        self.assertEqual(self.client.get('/api/game/goals',headers={'X-Academic-Year':'99'}).status_code,404)
        self.assertEqual(self.client.get('/api/game/goals',headers={'X-Academic-Year':'bad'}).status_code,400)
