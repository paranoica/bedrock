import sqlite3
def get_user(request, conn: sqlite3.Connection):
    uid = request.args.get("id")                      # untrusted source
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {uid}")  # SQLi sink  [VULN: sqli]
    return cur.fetchone()
