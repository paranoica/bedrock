import sqlite3
def get_user(request, conn: sqlite3.Connection):
    uid = request.args.get("id")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))  # parameterized — SAFE
    return cur.fetchone()
