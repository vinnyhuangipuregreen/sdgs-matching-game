import sqlite3
import json
import os
import hashlib
from pathlib import Path

def resolve_db_path():
    env_path = os.environ.get("SDGS_DB_PATH")
    if env_path:
        return Path(env_path)
    local_path = Path(__file__).parent.parent / "sdgs_game.db"
    try:
        test_conn = sqlite3.connect(local_path)
        test_conn.execute("CREATE TABLE IF NOT EXISTS _test (id INT);")
        test_conn.execute("DROP TABLE _test;")
        test_conn.close()
        return local_path
    except sqlite3.OperationalError:
        return Path("/tmp/sdgs_game.db")

DB_PATH = resolve_db_path()
DATA_JSON_PATH = Path(__file__).parent / "data.json"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

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

    conn.commit()
    conn.close()

def seed_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM goals;")
    if cursor.fetchone()[0] == 0:
        if DATA_JSON_PATH.exists():
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            for g in data["goals"]:
                cursor.execute("""
                INSERT INTO goals (id, code, name, full_name, category, category_zh, color, icon, slogan, example)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""", (
                    g["id"], g["code"], g["name"], g["full_name"],
                    g["category"], g["category_zh"], g["color"],
                    g.get("icon", "🎯"), g.get("slogan", ""), g.get("example", "")
                ))
                if g.get("slogan"):
                    cursor.execute("""
                    INSERT INTO scenarios (goal_id, scenario_text, real_life_example)
                    VALUES (?, ?, ?);""", (g["id"], g["slogan"], g.get("example", "")))

            for t in data["targets"]:
                cursor.execute("""
                INSERT INTO targets (id, code, goal_id, type, description, is_means)
                VALUES (?, ?, ?, ?, ?, ?);""", (
                    t["id"], t["code"], t["goal_id"], t["type"],
                    t["description"], 1 if t.get("is_means") else 0
                ))

            print("Seeded 17 goals and 169 targets into database.")

    default_pw_hash = hashlib.sha256("sdgs2030admin".encode("utf-8")).hexdigest()
    cursor.execute("""
    INSERT OR IGNORE INTO admin_users (username, password_hash, role)
    VALUES ('admin', ?, 'superadmin');""", (default_pw_hash,))

    default_settings = [
        ("time_limit_per_question", "20", "每題配對限制秒數"),
        ("points_base", "100", "基礎答對分數"),
        ("points_combo_bonus", "25", "每次連續答對之額外連擊加乘分"),
        ("points_penalty_wrong", "20", "答錯倒扣分數"),
        ("questions_per_game", "10", "每局遊戲配對題數"),
        ("leaderboard_display_limit", "20", "排行榜前台顯示名額")
    ]
    for k, v, desc in default_settings:
        cursor.execute("""
        INSERT OR IGNORE INTO system_settings (key, value, description)
        VALUES (?, ?, ?);""", (k, v, desc))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    seed_db()
    print("Database initialization complete.")
