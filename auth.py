"""Small, dependency-free auth: PBKDF2 password hashes + hashed session tokens in an httpOnly cookie."""
import hashlib, hmac, re, secrets
from datetime import datetime, timedelta, timezone
import database as db

COOKIE, DAYS = "sid", 30
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _now(): return datetime.now(timezone.utc)
def _th(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()

def new_salt() -> str: return secrets.token_hex(16)
def hash_pw(pw: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
def verify(pw: str, salt: str, expected: str) -> bool:
    return hmac.compare_digest(hash_pw(pw, salt), expected)

def start_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with db.conn() as c:
        c.execute("DELETE FROM sessions WHERE expires < ?", (_now().isoformat(),))
        c.execute("INSERT INTO sessions VALUES (?,?,?)", (_th(token), user_id, (_now() + timedelta(days=DAYS)).isoformat()))
    return token

def end_session(token):
    if token:
        with db.conn() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_th(token),))

def user_for(token):
    if not token:
        return None
    with db.conn() as c:
        r = c.execute("""SELECT u.id, u.email, u.display_name FROM sessions s JOIN users u ON u.id = s.user_id
                         WHERE s.token_hash=? AND s.expires > ?""", (_th(token), _now().isoformat())).fetchone()
    return dict(r) if r else None

# ---------- one-time tokens (email verification, password reset)
def make_token(user_id: int, kind: str, hours: int) -> str:
    token = secrets.token_urlsafe(32)
    with db.conn() as c:
        c.execute("DELETE FROM tokens WHERE user_id=? AND kind=?", (user_id, kind))   # a new link retires the old one
        c.execute("INSERT INTO tokens VALUES (?,?,?,?)", (_th(token), user_id, kind, (_now() + timedelta(hours=hours)).isoformat()))
    return token

def use_token(token: str, kind: str):
    """Returns the user id and burns the token, or None if it's wrong, expired or already used."""
    if not token:
        return None
    with db.conn() as c:
        r = c.execute("SELECT user_id FROM tokens WHERE token_hash=? AND kind=? AND expires > ?",
                      (_th(token), kind, _now().isoformat())).fetchone()
        if not r:
            return None
        c.execute("DELETE FROM tokens WHERE token_hash=?", (_th(token),))
    return r["user_id"]
