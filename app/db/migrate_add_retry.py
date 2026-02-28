from sqlalchemy import text
from app.db.session import engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0")
        )
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 3")
        )


if __name__ == "__main__":
    main()
