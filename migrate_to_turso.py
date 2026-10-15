"""Initialize Turso, or import an existing SQLite database into an empty Turso DB."""
import argparse
import sqlite3
from pathlib import Path
from app.database import get_db_connection, is_using_turso, init_db, seed_db

TABLES = (
    "goals", "targets", "scenarios", "challengers", "game_sessions",
    "game_details", "admin_users", "system_settings",
)


def import_sqlite(source_path, destination):
    source = sqlite3.connect(Path(source_path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        # Checks run under the same write lock as the import: never merge or overwrite.
        statements = [("CREATE TEMP TABLE import_guard (n INTEGER CHECK (n = 0))", ())]
        for table in TABLES:
            statements.append((f"INSERT INTO import_guard SELECT COUNT(*) FROM {table}", ()))
        counts = {}
        for table in TABLES:
            cursor = source.execute(f"SELECT * FROM {table}")
            columns = [item[0] for item in cursor.description]
            names = ", ".join('"' + c.replace('"', '""') + '"' for c in columns)
            placeholders = ", ".join("?" for _ in columns)
            rows = cursor.fetchall()
            counts[table] = len(rows)
            statements.extend((f"INSERT INTO {table} ({names}) VALUES ({placeholders})", row) for row in rows)
        statements.append(("INSERT INTO import_guard SELECT COUNT(*) FROM pragma_foreign_key_check", ()))
        statements.append(("DROP TABLE import_guard", ()))
        destination.execute_batch(statements)
        return counts
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-sqlite", type=Path, help="Import all existing records; destination must be empty")
    args = parser.parse_args()
    if not is_using_turso():
        parser.error("Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env or environment variables")
    init_db()
    if args.from_sqlite:
        conn = get_db_connection()
        try:
            counts = import_sqlite(args.from_sqlite, conn)
            print("Imported:", counts)
        finally:
            conn.close()
    # Adds missing standard content/settings without overwriting existing edits or passwords.
    seed_db()
    conn = get_db_connection()
    try:
        for table in TABLES:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count}")
    finally:
        conn.close()
    print("Turso initialization complete. Configure the same credentials in Vercel and redeploy.")


if __name__ == "__main__":
    main()
