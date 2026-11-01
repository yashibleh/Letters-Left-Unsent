"""Sliding-window attempt counter stored in the database, so limits survive restarts and are shared between serverless instances."""
import random, time
import database as db

def blocked(key: str, limit: int, window: int) -> int:
    """0 if allowed, otherwise the number of seconds until another attempt is allowed."""
    now = int(time.time())
    with db.conn() as c:
        rows = c.execute("SELECT ts FROM attempts WHERE key=? AND ts > ? ORDER BY ts", (key, now - window)).fetchall()
    if len(rows) >= limit:
        return max(1, rows[len(rows) - limit]["ts"] + window - now)
    return 0

def hit(key: str):
    now = int(time.time())
    with db.conn() as c:
        c.execute("INSERT INTO attempts VALUES (?,?)", (key, now))
        if random.random() < 0.02:                  # now and then, tidy up old rows (saves a round trip on every call)
            c.execute("DELETE FROM attempts WHERE ts < ?", (now - 86400,))

def clear(key: str):
    with db.conn() as c:
        c.execute("DELETE FROM attempts WHERE key=?", (key,))
