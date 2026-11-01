"""Database access.  DATABASE_URL set (Neon / any Postgres) -> Postgres.  Not set -> a local SQLite file, for quick local tests only.
All SQL in the app is written with ? placeholders; this module adapts them for Postgres.
Postgres connections are kept and reused (opening one costs several round trips) and run in autocommit mode,
so each statement is one round trip."""
import os, queue, sqlite3, time
from pathlib import Path
import config  # noqa: F401  (loads .env first)

URL = os.getenv("DATABASE_URL", "").strip()
POSTGRES = URL.startswith(("postgres://", "postgresql://"))
SQLITE_PATH = os.getenv("SQLITE_PATH") or str(Path(__file__).parent / "letters.db")

if POSTGRES:
    import psycopg
    from psycopg.rows import dict_row
    IntegrityError = psycopg.IntegrityError
else:
    IntegrityError = sqlite3.IntegrityError

_ready = False
_POOL: "queue.LifoQueue" = queue.LifoQueue()      # idle connections: (connection, time last used)
_POOL_MAX = 4
_IDLE_PING = 20                                   # seconds idle before a connection is tested before reuse

def describe() -> str:
    return "Postgres (DATABASE_URL is set)" if POSTGRES else f"local SQLite file {SQLITE_PATH}  (set DATABASE_URL to use Neon)"

def _connect(autocommit: bool):
    return psycopg.connect(URL, autocommit=autocommit, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)

def _close(c):
    try: c.close()
    except Exception: pass

def _acquire():
    while True:
        try:
            c, last = _POOL.get_nowait()
        except queue.Empty:
            return _connect(True)
        if c.closed or c.broken:
            continue
        if time.time() - last > _IDLE_PING:         # the server may have dropped it while idle
            try:
                c.execute("SELECT 1")
            except Exception:
                _close(c); continue
        return c

def _release(c):
    if c.closed or c.broken:
        _close(c); return
    if _POOL.qsize() < _POOL_MAX:
        _POOL.put((c, time.time()))
    else:
        _close(c)

class _Conn:
    def __init__(self, ensure: bool = True, ddl: bool = False):
        if ensure:
            ensure_ready()
        self.ddl, self.used = ddl, False
        if POSTGRES:
            self.c = _connect(False) if ddl else _acquire()      # the table-creation step needs a real transaction
        else:
            if os.getenv("VERCEL"):
                raise RuntimeError("DATABASE_URL is not set. Add your Neon connection string in the Vercel project's environment variables.")
            self.c = sqlite3.connect(SQLITE_PATH)
            self.c.row_factory = sqlite3.Row

    def execute(self, sql, params=None):
        if not POSTGRES:
            return self.c.execute(sql, params or ())
        sql = sql.replace("?", "%s")
        first, self.used = not self.used, True
        try:
            return self.c.execute(sql, params)
        except (psycopg.OperationalError, psycopg.InterfaceError):
            if not first or self.ddl:
                raise
            _close(self.c); self.c = _connect(True)         # a reused connection had gone stale: reconnect once
            return self.c.execute(sql, params)

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if POSTGRES and not self.ddl:
            _release(self.c)                                # autocommit: nothing to commit or roll back
            return False
        try:
            self.c.commit() if et is None else self.c.rollback()
        finally:
            self.c.close()
        return False

def conn() -> _Conn:
    return _Conn()

_NOW = "to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')"

def _create_postgres(c: _Conn):
    c.execute("SELECT pg_advisory_xact_lock(727272)")      # several cold starts may race to create tables
    c.execute(f"""CREATE TABLE IF NOT EXISTS letters (
        id BIGSERIAL PRIMARY KEY, recipient TEXT DEFAULT '', content TEXT NOT NULL, author_token TEXT DEFAULT '',
        user_id BIGINT, timestamp TEXT DEFAULT {_NOW}, scheduled_date TEXT, echo_count INTEGER DEFAULT 0,
        ambient_audio_choice TEXT DEFAULT 'none')""")
    c.execute(f"""CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, display_name TEXT DEFAULT '',
        pw_hash TEXT NOT NULL, salt TEXT NOT NULL, created TEXT DEFAULT {_NOW}, verified INTEGER DEFAULT 0)""")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id BIGINT NOT NULL, expires TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS tokens (token_hash TEXT PRIMARY KEY, user_id BIGINT NOT NULL, kind TEXT NOT NULL, expires TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS attempts (key TEXT NOT NULL, ts BIGINT NOT NULL)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_attempts ON attempts(key, ts)")

def _create_sqlite(c: _Conn):
    c.execute("""CREATE TABLE IF NOT EXISTS letters (
        id INTEGER PRIMARY KEY AUTOINCREMENT, recipient TEXT DEFAULT '', content TEXT NOT NULL, author_token TEXT DEFAULT '',
        user_id INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, scheduled_date TEXT, echo_count INTEGER DEFAULT 0,
        ambient_audio_choice TEXT DEFAULT 'none')""")
    if "user_id" not in [r["name"] for r in c.execute("PRAGMA table_info(letters)")]:
        c.execute("ALTER TABLE letters ADD COLUMN user_id INTEGER")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, display_name TEXT DEFAULT '',
        pw_hash TEXT NOT NULL, salt TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    if "verified" not in [r["name"] for r in c.execute("PRAGMA table_info(users)")]:
        c.execute("ALTER TABLE users ADD COLUMN verified INTEGER DEFAULT 0")
        c.execute("UPDATE users SET verified=1")
    c.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS tokens (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, kind TEXT NOT NULL, expires TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS attempts (key TEXT NOT NULL, ts INTEGER NOT NULL)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_attempts ON attempts(key, ts)")

def ensure_ready():
    """Creates the tables once per process (so a cold start pays for it once)."""
    global _ready
    if _ready:
        return
    with _Conn(ensure=False, ddl=True) as c:
        (_create_postgres if POSTGRES else _create_sqlite)(c)
    _ready = True

init_db = ensure_ready
