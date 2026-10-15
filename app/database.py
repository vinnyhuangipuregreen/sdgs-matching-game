import sqlite3
import json
import os
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def resolve_db_path():
    env_path = os.environ.get("SDGS_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parent.parent / "sdgs_game.db"

def resolve_data_json_path():
    candidates = [
        Path(__file__).resolve().parent / "data.json",
        Path(__file__).parent / "data.json",
        Path.cwd() / "app" / "data.json"
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

DB_PATH = resolve_db_path()
DATA_JSON_PATH = resolve_data_json_path()

# ==========================================
# Turso Cloud (libSQL over HTTP) Adapter
# ==========================================

class TursoRow:
    def __init__(self, cols, values):
        self._cols = cols
        self._values = values
        self._dict = dict(zip(cols, values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._dict[key]

    def get(self, key, default=None):
        return self._dict.get(key, default)

    def keys(self):
        return self._cols

    def items(self):
        return self._dict.items()

    def values(self):
        return self._values

    def __iter__(self):
        return iter(self._values)

    def __contains__(self, key):
        return key in self._dict

    def __repr__(self):
        return f"TursoRow({self._dict})"


class TursoCursor:
    def __init__(self, conn):
        self.conn = conn
        self.description = None
        self._rows = []
        self._row_idx = 0
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, sql, params=()):
        result = self.conn._execute_remote(sql, params)
        cols = [c.get("name", f"col_{i}") for i, c in enumerate(result.get("cols", []))]
        self.description = [(name, None, None, None, None, None, None) for name in cols]

        last_id = result.get("last_insert_rowid")
        if last_id is not None:
            try:
                self.lastrowid = int(last_id)
            except (ValueError, TypeError):
                self.lastrowid = last_id
        else:
            self.lastrowid = None

        self.rowcount = result.get("affected_row_count", 0)

        parsed_rows = []
        for raw_row in result.get("rows", []):
            vals = [self._parse_cell(cell) for cell in raw_row]
            parsed_rows.append(TursoRow(cols, vals))

        self._rows = parsed_rows
        self._row_idx = 0
        return self

    def executemany(self, sql, seq_of_params):
        requests = []
        for p in seq_of_params:
            requests.append({
                "type": "execute",
                "stmt": {
                    "sql": sql,
                    "args": [self.conn._format_arg(v) for v in p]
                }
            })
        if requests:
            self.conn._execute_pipeline(requests)
        return self

    def _parse_cell(self, cell):
        if not cell or cell.get("type") == "null":
            return None
        t = cell.get("type")
        val = cell.get("value")
        if t == "integer":
            try:
                return int(val)
            except (ValueError, TypeError):
                return val
        elif t == "float":
            try:
                return float(val)
            except (ValueError, TypeError):
                return val
        return val

    def fetchone(self):
        if self._row_idx < len(self._rows):
            row = self._rows[self._row_idx]
            self._row_idx += 1
            return row
        return None

    def fetchall(self):
        remaining = self._rows[self._row_idx:]
        self._row_idx = len(self._rows)
        return remaining

    def close(self):
        pass


class TursoConnection:
    def __init__(self, url, auth_token):
        clean_url = url.strip()
        if clean_url.startswith("libsql://"):
            clean_url = "https://" + clean_url[9:]
        elif clean_url.startswith("turso://"):
            clean_url = "https://" + clean_url[8:]
        parsed = urlsplit(clean_url)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username or parsed.password
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.hostname in ("app.turso.tech", "turso.tech")):
            raise ValueError("TURSO_DATABASE_URL must be the HTTPS/libsql database URL, not a dashboard URL")
        self.base_url = clean_url.rstrip("/")
        self.endpoint = f"{self.base_url}/v2/pipeline"
        self.auth_token = auth_token.strip()

    def _format_arg(self, val):
        if val is None:
            return {"type": "null"}
        elif isinstance(val, bool):
            return {"type": "integer", "value": "1" if val else "0"}
        elif isinstance(val, int):
            return {"type": "integer", "value": str(val)}
        elif isinstance(val, float):
            return {"type": "float", "value": val}
        else:
            return {"type": "text", "value": str(val)}

    def _execute_pipeline(self, requests_list):
        payload = {
            "requests": [{"type": "execute", "stmt": {"sql": "PRAGMA foreign_keys = ON"}}]
                        + requests_list + [{"type": "close"}]
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=req_data,
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Turso HTTP Error {e.code}: {err_body}")
        except Exception as e:
            raise RuntimeError(f"Turso Connection Error: {e}")

        results = resp_json.get("results", [])
        for res in results:
            if res.get("type") == "error":
                raise RuntimeError(f"Turso Pipeline Query Error: {res.get('error', {}).get('message')}")
            for error in res.get("response", {}).get("result", {}).get("step_errors", []):
                if error:
                    raise RuntimeError(f"Turso Batch Query Error: {error.get('message')}")
        return results[1:]

    def execute_batch(self, statements):
        """Execute an atomic transaction in one HTTP round trip."""
        steps = [{"stmt": {"sql": "BEGIN IMMEDIATE"}}]
        for sql, params in statements:
            steps.append({
                "condition": {"type": "ok", "step": len(steps) - 1},
                "stmt": {"sql": sql, "args": [self._format_arg(v) for v in params]},
            })
        steps.append({
            "condition": {"type": "ok", "step": len(steps) - 1},
            "stmt": {"sql": "COMMIT"},
        })
        steps.append({
            "condition": {"type": "not", "cond": {"type": "ok", "step": len(steps) - 1}},
            "stmt": {"sql": "ROLLBACK"},
        })
        self._execute_pipeline([{"type": "batch", "batch": {"steps": steps}}])

    def _execute_remote(self, sql, params=()):
        args = [self._format_arg(p) for p in params]
        requests = [
            {
                "type": "execute",
                "stmt": {
                    "sql": sql,
                    "args": args
                }
            }
        ]
        results = self._execute_pipeline(requests)
        if not results or "result" not in results[0].get("response", {}):
            raise RuntimeError("Invalid Turso query response")
        return results[0]["response"]["result"]

    def cursor(self):
        return TursoCursor(self)

    def execute(self, sql, params=()):
        cur = self.cursor()
        return cur.execute(sql, params)

    def commit(self):
        pass

    def close(self):
        pass


def get_db_connection():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    if is_using_turso():
        return TursoConnection(turso_url, turso_token)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def is_using_turso():
    url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
    if bool(url) != bool(token) or (os.environ.get("VERCEL") and not (url and token)):
        raise RuntimeError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are both required on Vercel or when using Turso")
    return bool(url and token)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        category TEXT NOT NULL,
        category_zh TEXT NOT NULL,
        color TEXT NOT NULL,
        icon TEXT,
        slogan TEXT,
        example TEXT,
        is_active INTEGER DEFAULT 1
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL UNIQUE,
        goal_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        description TEXT NOT NULL,
        is_means INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scenarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        scenario_text TEXT NOT NULL,
        real_life_example TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (goal_id) REFERENCES goals (id) ON DELETE CASCADE
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS challengers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL,
        organization TEXT DEFAULT '一般挑戰者',
        avatar TEXT DEFAULT '🌱',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenger_id INTEGER NOT NULL,
        mode TEXT NOT NULL,
        difficulty TEXT DEFAULT 'medium',
        total_score INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        combo_max INTEGER DEFAULT 0,
        time_taken_seconds REAL DEFAULT 0,
        completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (challenger_id) REFERENCES challengers (id) ON DELETE CASCADE
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        target_id INTEGER,
        goal_id INTEGER NOT NULL,
        selected_goal_id INTEGER,
        is_correct INTEGER NOT NULL,
        time_spent_ms INTEGER DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES game_sessions (id) ON DELETE CASCADE,
        FOREIGN KEY (goal_id) REFERENCES goals (id)
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );""")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_targets_goal ON targets (goal_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_score ON game_sessions (total_score DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_challenger ON game_sessions (challenger_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_details_session ON game_details (session_id);")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_sessions (
        token_hash TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        expires_at REAL NOT NULL
    );""")

    conn.commit()
    conn.close()

def seed_db():
    # One atomic batch avoids partial seeds and concurrent cold-start races.
    with open(DATA_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    conn = get_db_connection()
    try:
        admin = conn.execute("SELECT 1 FROM admin_users LIMIT 1").fetchone()
        password = os.environ.get("SDGS_ADMIN_PASSWORD", "").strip()
        if not admin and not password:
            if is_using_turso():
                raise RuntimeError("Set SDGS_ADMIN_PASSWORD before initializing a new Turso database")
            password = "sdgs2030admin"
        statements = []
        for g in data["goals"]:
            statements.append(("""
                INSERT OR IGNORE INTO goals
                (id, code, name, full_name, category, category_zh, color, icon, slogan, example)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (g["id"], g["code"], g["name"], g["full_name"], g["category"],
                  g["category_zh"], g["color"], g.get("icon", "🎯"),
                  g.get("slogan", ""), g.get("example", ""))))
            if g.get("slogan"):
                statements.append(("""
                    INSERT INTO scenarios (goal_id, scenario_text, real_life_example)
                    SELECT ?, ?, ? WHERE NOT EXISTS
                    (SELECT 1 FROM scenarios WHERE goal_id = ?)
                """, (g["id"], g["slogan"], g.get("example", ""), g["id"])))
        for t in data["targets"]:
            statements.append(("""
                INSERT OR IGNORE INTO targets (id, code, goal_id, type, description, is_means)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (t["id"], t["code"], t["goal_id"], t["type"],
                  t["description"], int(bool(t.get("is_means"))))))
        if not admin:
            statements.append(("""
                INSERT OR IGNORE INTO admin_users (username, password_hash, role)
                VALUES ('admin', ?, 'superadmin')
            """, (hashlib.sha256(password.encode("utf-8")).hexdigest(),)))
        default_settings = [
            ("time_limit_per_question", "20", "每題配對限制秒數"),
            ("points_base", "100", "基礎答對分數"),
            ("points_combo_bonus", "25", "每次連續答對之額外連擊加乘分"),
            ("points_penalty_wrong", "20", "答錯倒扣分數"),
            ("questions_per_game", "10", "每局遊戲配對題數"),
            ("leaderboard_display_limit", "20", "排行榜前台顯示名額"),
        ]
        statements.extend(("""
            INSERT OR IGNORE INTO system_settings (key, value, description) VALUES (?, ?, ?)
        """, setting) for setting in default_settings)
        if isinstance(conn, TursoConnection):
            conn.execute_batch(statements)
        else:
            with conn:
                for sql, params in statements:
                    conn.execute(sql, params)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    db_mode = "Turso Cloud" if is_using_turso() else f"Local SQLite ({DB_PATH})"
    print(f"Database ready: {db_mode}")
