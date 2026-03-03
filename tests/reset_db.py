from sqlalchemy import text
from app.db.session import engine

def main():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM job_events"))
        conn.execute(text("DELETE FROM jobs"))
        print("✅ Database wiped clean")

if __name__ == "__main__":
    main()