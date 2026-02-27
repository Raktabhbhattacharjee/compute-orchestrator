from sqlalchemy import text
from app.db.session import engine

def column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table});")).fetchall()
    return any(r[1] == column for r in rows)

with engine.begin() as conn:
    if column_exists(conn, "jobs", "last_heartbeat_at"):
        print("Column already exists. Skipping migration.")
    else:
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN last_heartbeat_at DATETIME;")
        )
        print("Column added successfully.")