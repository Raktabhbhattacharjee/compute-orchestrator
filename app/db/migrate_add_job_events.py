from sqlalchemy import text
from app.db.session import engine
#  function for creating it 
def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL REFERENCES jobs(id),
                from_status VARCHAR,
                to_status VARCHAR NOT NULL,
                actor VARCHAR(128),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        print("job_events table created successfully")

if __name__ == "__main__":
    main()