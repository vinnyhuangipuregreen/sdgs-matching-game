"""Turso HTTP contract tests backed by SQLite; no cloud credentials are used."""
import importlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import auth, database
from app.main import app
from migrate_to_turso import import_sqlite
from tests import test_api


class HranaServer:
    def __init__(self, path):
        self.path = path

    def urlopen(self, request, timeout):
        payload = json.loads(request.data)
        conn = sqlite3.connect(self.path, isolation_level=None)
        def execute(stmt):
            cursor = conn.execute(stmt['sql'], [self.decode(v) for v in stmt.get('args', [])])
            cols = [{'name': c[0]} for c in cursor.description or []]
            rows = [[self.encode(v) for v in row] for row in cursor.fetchall()]
            return {'cols': cols, 'rows': rows, 'affected_row_count': max(cursor.rowcount, 0),
                    'last_insert_rowid': str(cursor.lastrowid) if cursor.lastrowid else None}
        results = []
        try:
            for item in payload['requests']:
                try:
                    if item['type'] == 'execute':
                        response = {'type': 'execute', 'result': execute(item['stmt'])}
                    elif item['type'] == 'batch':
                        successes, errors = [], []
                        def condition(c):
                            if c['type'] == 'ok':
                                return successes[c['step']] is not None
                            if c['type'] == 'not':
                                return not condition(c['cond'])
                            raise AssertionError(c)
                        for step in item['batch']['steps']:
                            if 'condition' in step and not condition(step['condition']):
                                successes.append(None)
                                errors.append(None)
                                continue
                            try:
                                successes.append(execute(step['stmt']))
                                errors.append(None)
                            except sqlite3.Error as e:
                                successes.append(None)
                                errors.append({'message': str(e)})
                        response = {'type': 'batch', 'result': {'step_results': successes, 'step_errors': errors}}
                    else:
                        response = {'type': 'close'}
                    results.append({'type': 'ok', 'response': response})
                except sqlite3.Error as e:
                    results.append({'type': 'error', 'error': {'message': str(e)}})
        finally:
            conn.close()
        return io.BytesIO(json.dumps({'results': results}).encode())

    @staticmethod
    def decode(cell):
        kind = cell['type']
        value = cell.get('value')
        return int(value) if kind == 'integer' else float(value) if kind == 'float' else value

    @staticmethod
    def encode(value):
        if value is None:
            return {'type': 'null'}
        if isinstance(value, int):
            return {'type': 'integer', 'value': str(value)}
        if isinstance(value, float):
            return {'type': 'float', 'value': value}
        return {'type': 'text', 'value': value}


class TestTursoAPI(test_api.TestSDGsGameAPI):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = HranaServer(Path(cls.temp.name) / 'cloud.db')
        cls.env_patch = patch.dict(os.environ, {
            'TURSO_DATABASE_URL': 'libsql://test.turso.io', 'TURSO_AUTH_TOKEN': 'test-token',
            'VERCEL': '1', 'SDGS_ADMIN_PASSWORD': 'sdgs2030admin',
        })
        cls.env_patch.start()
        cls.db_patch = patch('urllib.request.urlopen', cls.server.urlopen)
        cls.db_patch.start()
        database.init_db()
        database.seed_db()
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    def test_seed_is_repeatable_and_preserves_edits(self):
        conn = database.get_db_connection()
        original = conn.execute('SELECT description FROM targets WHERE id = 1').fetchone()[0]
        try:
            conn.execute("UPDATE targets SET description = 'edited', is_active = 0 WHERE id = 1")
            database.seed_db()
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM goals').fetchone()[0], 17)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM targets').fetchone()[0], 169)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM scenarios').fetchone()[0], 17)
            self.assertEqual(list(conn.execute('SELECT description, is_active FROM targets WHERE id = 1').fetchone()), ['edited', 0])
        finally:
            conn.execute('UPDATE targets SET description = ?, is_active = 1 WHERE id = 1', (original,))
            conn.close()

    def test_admin_survives_module_reload_and_expires(self):
        token = auth.create_admin_session('admin')
        importlib.reload(auth)
        self.assertEqual(auth.verify_admin_token('Bearer ' + token, None)['username'], 'admin')
        conn = database.get_db_connection()
        conn.execute('UPDATE admin_sessions SET expires_at = 0 WHERE token_hash = ?', (auth.hash_password(token),))
        conn.close()
        self.assertEqual(self.client.get('/api/admin/stats', headers={'Authorization': 'Bearer ' + token}).status_code, 401)

    def test_atomic_batch_rolls_back(self):
        conn = database.get_db_connection()
        with self.assertRaises(RuntimeError):
            conn.execute_batch([
                ("INSERT INTO system_settings (key, value) VALUES ('rollback_test', '1')", ()),
                ('INSERT INTO missing_table VALUES (1)', ()),
            ])
        self.assertIsNone(conn.execute("SELECT value FROM system_settings WHERE key = 'rollback_test'").fetchone())

    def test_answer_uses_one_round_trip_and_current_settings(self):
        started = self.client.post('/api/game/start', json={'nickname': 'latency-test', 'mode': 'standard', 'question_count': 1}).json()
        question = started['questions'][0]
        conn = database.get_db_connection()
        conn.execute("UPDATE system_settings SET value = '137' WHERE key = 'points_base'")
        payload = {
            'session_id': started['session_id'], 'question_index': 0,
            'target_id': question['target_id'], 'selected_goal_id': question['correct_goal_id'],
            'correct_goal_id': question['correct_goal_id'], 'current_combo': 1,
        }
        try:
            with patch('urllib.request.urlopen', wraps=self.server.urlopen) as requests:
                response = self.client.post('/api/game/answer', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['score_delta'], 162)
            self.assertEqual(response.json()['target']['id'], question['target_id'])
            self.assertEqual(requests.call_count, 1)
            payload.update(target_id=None, selected_goal_id=1 if question['correct_goal_id'] != 1 else 2)
            with patch('urllib.request.urlopen', wraps=self.server.urlopen) as requests:
                response = self.client.post('/api/game/answer', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['is_correct'])
            self.assertEqual(response.json()['score_delta'], -20)
            self.assertIsNone(response.json()['target'])
            self.assertEqual(requests.call_count, 1)
        finally:
            conn.execute("UPDATE system_settings SET value = '100' WHERE key = 'points_base'")

    def test_foreign_keys_and_cascade(self):
        conn = database.get_db_connection()
        with self.assertRaises(RuntimeError):
            conn.execute('INSERT INTO game_sessions (challenger_id, mode) VALUES (-999, ?)', ('standard',))
        challenger = conn.execute("INSERT INTO challengers (nickname) VALUES ('cascade')").lastrowid
        session = conn.execute("INSERT INTO game_sessions (challenger_id, mode) VALUES (?, 'standard')", (challenger,)).lastrowid
        conn.execute('INSERT INTO game_details (session_id, goal_id, is_correct) VALUES (?, 1, 1)', (session,))
        conn.execute('DELETE FROM game_sessions WHERE id = ?', (session,))
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM game_details WHERE session_id = ?', (session,)).fetchone()[0], 0)

    def test_routes_and_all_modes(self):
        for path in ('/', '/admin', '/static/js/game.js', '/static/js/admin.js', '/static/css/style.css', '/api/game/handbook'):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertEqual(self.client.get('/healthz').json(), {'status': 'ok', 'database': 'turso'})
        for mode in ('scenario', 'standard', 'cards', 'master169'):
            response = self.client.post('/api/game/start', json={'nickname': 'test', 'mode': mode, 'question_count': 5})
            self.assertEqual(response.status_code, 200, response.text)
        token = auth.create_admin_session('admin')
        response = self.client.get('/api/admin/export/csv', headers={'Authorization': 'Bearer ' + token})
        self.assertEqual(response.status_code, 200)
        self.assertIn('永續小英雄', response.text)
        self.assertIn('標準細項配對', response.text)
        self.assertNotIn('nickname,organization', response.text)

    def test_import_refuses_populated_destination(self):
        conn = database.get_db_connection()
        with self.assertRaises(RuntimeError):
            import_sqlite(self.server.path, conn)
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM targets').fetchone()[0], 169)

    def test_import_preserves_all_records_and_ids(self):
        destination = HranaServer(Path(self.temp.name) / 'import.db')
        with patch('urllib.request.urlopen', destination.urlopen):
            database.init_db()
            conn = database.get_db_connection()
            counts = import_sqlite(self.server.path, conn)
            for table, count in counts.items():
                self.assertEqual(conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], count)
            database.seed_db()
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM targets').fetchone()[0], 169)
            self.assertEqual(conn.execute('SELECT nickname FROM challengers WHERE id = 1').fetchone()[0], '永續小英雄')
            self.assertEqual(conn.execute('SELECT total_score FROM game_sessions WHERE id = 1').fetchone()[0], 600)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM admin_sessions').fetchone()[0], 0)


class TestConfiguration(unittest.TestCase):
    def test_missing_cloud_credentials_never_fall_back(self):
        for values in ({'VERCEL': '1'}, {'TURSO_DATABASE_URL': 'libsql://test.turso.io'}, {'TURSO_AUTH_TOKEN': 'token'}):
            with patch.dict(os.environ, {'VERCEL': '', 'TURSO_DATABASE_URL': '', 'TURSO_AUTH_TOKEN': '', **values}):
                with self.assertRaises(RuntimeError):
                    database.get_db_connection()

    def test_reject_dashboard_and_insecure_urls(self):
        for url in ('https://app.turso.tech/vinnyhuangipuregreen', 'http://db.turso.io', 'https://db.turso.io/wrong'):
            with self.assertRaises(ValueError):
                database.TursoConnection(url, 'token')

    def test_main_exports_fastapi(self):
        from main import app as exported
        self.assertIs(exported, app)


if __name__ == '__main__':
    unittest.main()
