from sqlalchemy import text
from app.db.session import engine


def main() -> None:
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 1")
        )


if __name__ == "__main__":
    main()
