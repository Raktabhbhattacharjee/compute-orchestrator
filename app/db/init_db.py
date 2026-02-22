from app.db.base import Base
from app.db.session import engine

# Ensure model is imported
from app.models.job import Job  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


if __name__ == "__main__":
    init_db()