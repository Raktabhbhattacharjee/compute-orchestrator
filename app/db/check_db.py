import sqlite3

def check_db():
    con = sqlite3.connect("compute_orchestrator.db")
    tables = con.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print("Tables:", tables)

if __name__ == "__main__":
    check_db()
