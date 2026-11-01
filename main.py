import config  # noqa: F401  (loads .env before anything reads settings)
import os, threading, time
from datetime import date
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
import auth, database as db, mailer, ml_filter, ratelimit

ON_VERCEL = bool(os.getenv("VERCEL"))
SYNC_MAIL = ON_VERCEL or os.getenv("MAIL_SYNC") == "1"   # on Vercel the function can freeze after replying, so mail goes out first
app = FastAPI(title="Letters Left Unsent", docs_url=None if ON_VERCEL else "/docs", redoc_url=None,
              openapi_url=None if ON_VERCEL else "/openapi.json")
AUDIO = {"none", "rain", "vinyl", "wind", "night"}
print(f"[db] using {db.describe()}", flush=True)

@app.middleware("http")
async def no_store(request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"       # the wall and drawer must never come from a stale copy
    return resp

if not ON_VERCEL:
    def _warm():
        try:
            db.ensure_ready()
            with db.conn() as c:
                c.execute("SELECT 1 FROM letters LIMIT 1").fetchall()
            ml_filter.load_models()
            print("[warm-up] database and filter models are ready", flush=True)
        except Exception as e:
            print(f"[warm-up] problem: {e}", flush=True)

    @app.on_event("startup")
    def _startup():
        threading.Thread(target=_warm, daemon=True).start()   # so the first letter doesn't pay for loading the models

# ---------- models
class DraftIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=3000)

class LetterIn(DraftIn):
    recipient: str = Field("", max_length=60)
    scheduled_date: Optional[str] = None   # YYYY-MM-DD
    ambient_audio_choice: str = "none"      # legacy column, no longer used by the site
    author_token: str = Field("", max_length=64)

class AuthIn(BaseModel):
    email: str = Field(..., max_length=120)
    password: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field("", max_length=40)
    claim_token: str = Field("", max_length=64)   # lets an account adopt letters written anonymously in this browser

class EmailIn(BaseModel):
    email: str = Field(..., max_length=120)

class TokenIn(BaseModel):
    token: str = Field(..., max_length=200)

class ResetIn(TokenIn):
    password: str = Field(..., min_length=1, max_length=128)

# ---------- helpers
def _ip(request: Request) -> str:
    if ON_VERCEL:   # Vercel sets these headers itself, so they can be trusted there
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
        if request.headers.get("x-real-ip"):
            return request.headers["x-real-ip"]
    return request.client.host if request.client else "unknown"

def _too_many(wait: int) -> HTTPException:
    mins = max(1, round(wait / 60))
    return HTTPException(429, f"Too many tries. Please wait about {mins} minute{'s' if mins != 1 else ''} and try again.",
                         headers={"Retry-After": str(wait)})

def throttle(key: str, limit: int, window: int):
    """Count one attempt against `key`; raise 429 if it is over the limit."""
    wait = ratelimit.blocked(key, limit, window)
    if wait:
        raise _too_many(wait)
    ratelimit.hit(key)

def _claim(uid: int, tok: str):
    if tok:
        with db.conn() as c:
            c.execute("UPDATE letters SET user_id=? WHERE author_token=? AND user_id IS NULL", (uid, tok))

def _mail(to: str, subject: str, body: str):
    if SYNC_MAIL:
        mailer.send(to, subject, body)
    else:                                                  # locally: don't make the visitor wait for the mail service
        threading.Thread(target=mailer.send, args=(to, subject, body), daemon=True).start()

def _pad():
    if SYNC_MAIL:
        time.sleep(0.4)      # roughly the time a send takes, so the answer doesn't give an address away

def _send_verification(uid: int, email: str):
    t = auth.make_token(uid, "verify", 24)
    _mail(email, "Confirm your email for Letters Left Unsent",
        f"Welcome to Letters Left Unsent.\n\nConfirm your email to open your drawer:\n{mailer.base_url()}/verify.html?token={t}\n\n"
        "This link works for 24 hours. If you didn't make an account, you can ignore this message.")

def _cookie_secure() -> bool:
    return ON_VERCEL or os.getenv("COOKIE_SECURE") == "1"

# ---------- auth
@app.post("/api/auth/register")
def register(a: AuthIn, request: Request):
    throttle(f"register:i:{_ip(request)}", 8, 3600)
    email = a.email.strip().lower()
    if not auth.EMAIL_RE.match(email):
        raise HTTPException(400, "That email doesn't look quite right.")
    if len(a.password) < 8:
        raise HTTPException(400, "Please choose a password of at least 8 characters.")
    salt = auth.new_salt()
    try:
        with db.conn() as c:
            uid = c.execute("INSERT INTO users (email, display_name, pw_hash, salt, verified) VALUES (?,?,?,?,0) RETURNING id",
                            (email, a.display_name.strip(), auth.hash_pw(a.password, salt), salt)).fetchone()["id"]
    except db.IntegrityError:
        raise HTTPException(409, "That email already has a drawer. Try signing in instead.")
    _claim(uid, a.claim_token)
    _send_verification(uid, email)
    return {"needs_verification": True, "mail": mailer.mode()}

@app.post("/api/auth/login")
def login(a: AuthIn, request: Request, response: Response):
    email, ip = a.email.strip().lower(), _ip(request)
    ek, ik = f"login:e:{email}", f"login:i:{ip}"
    for key, limit in ((ek, 5), (ik, 30)):          # 5 misses per email, 30 per address, per 15 minutes
        wait = ratelimit.blocked(key, limit, 900)
        if wait:
            raise _too_many(wait)
    with db.conn() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if u:
        ok = auth.verify(a.password, u["salt"], u["pw_hash"])
    else:
        auth.hash_pw(a.password, "00" * 16); ok = False   # same work either way, so timing doesn't reveal which emails exist
    if not ok:
        ratelimit.hit(ek); ratelimit.hit(ik)
        raise HTTPException(401, "That email and password don't match.")
    if not u["verified"]:
        return JSONResponse(status_code=403, content={"needs_verification": True,
            "detail": "Please confirm your email first. The link we sent is waiting in your inbox."})
    ratelimit.clear(ek)
    _claim(u["id"], a.claim_token)
    response.set_cookie(auth.COOKIE, auth.start_session(u["id"]), httponly=True, samesite="lax",
                        secure=_cookie_secure(), max_age=auth.DAYS * 86400)
    return {"user": {"id": u["id"], "email": u["email"], "display_name": u["display_name"]}}

@app.post("/api/auth/verify")
def verify_email(t: TokenIn):
    uid = auth.use_token(t.token, "verify")
    if not uid:
        raise HTTPException(400, "This link has expired or was already used. If you've already confirmed, just sign in.")
    with db.conn() as c:
        c.execute("UPDATE users SET verified=1 WHERE id=?", (uid,))
    return {"ok": True}

@app.post("/api/auth/resend")
def resend(a: EmailIn, request: Request):
    email = a.email.strip().lower()
    throttle(f"resend:e:{email}", 3, 3600); throttle(f"resend:i:{_ip(request)}", 10, 3600)
    with db.conn() as c:
        u = c.execute("SELECT id, verified FROM users WHERE email=?", (email,)).fetchone()
    if u and not u["verified"]:
        _send_verification(u["id"], email)
    else:
        _pad()
    return {"ok": True, "mail": mailer.mode()}        # same answer whether or not the email exists

@app.post("/api/auth/forgot")
def forgot(a: EmailIn, request: Request):
    email = a.email.strip().lower()
    throttle(f"forgot:e:{email}", 3, 3600); throttle(f"forgot:i:{_ip(request)}", 10, 3600)
    with db.conn() as c:
        u = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if u:
        t = auth.make_token(u["id"], "reset", 1)
        _mail(email, "Reset your Letters Left Unsent password",
            f"Someone (hopefully you) asked to reset the password for this email.\n\nChoose a new one here:\n{mailer.base_url()}/reset.html?token={t}\n\n"
            "This link works for one hour. If you didn't ask for it, you can ignore this message and nothing will change.")
    else:
        _pad()
    return {"ok": True, "mail": mailer.mode()}

@app.post("/api/auth/reset")
def reset(r: ResetIn):
    if len(r.password) < 8:
        raise HTTPException(400, "Please choose a password of at least 8 characters.")
    uid = auth.use_token(r.token, "reset")
    if not uid:
        raise HTTPException(400, "This link has expired or was already used. You can ask for a new one.")
    salt = auth.new_salt()
    with db.conn() as c:
        c.execute("UPDATE users SET pw_hash=?, salt=?, verified=1 WHERE id=?", (auth.hash_pw(r.password, salt), salt, uid))
        c.execute("DELETE FROM sessions WHERE user_id=?", (uid,))      # signs out every device
        email = c.execute("SELECT email FROM users WHERE id=?", (uid,)).fetchone()["email"]
    ratelimit.clear(f"login:e:{email}")
    return {"ok": True}

@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    auth.end_session(request.cookies.get(auth.COOKIE))
    response.delete_cookie(auth.COOKIE)
    return {"ok": True}

@app.get("/api/auth/me")
def me(request: Request):
    return {"user": auth.user_for(request.cookies.get(auth.COOKIE))}

# ---------- letters
@app.get("/api/health")
def health():
    return {"ok": True, "database": "postgres" if db.POSTGRES else "sqlite"}

@app.post("/api/validate")
def validate(d: DraftIn, request: Request):
    throttle(f"validate:i:{_ip(request)}", 30, 600)
    return ml_filter.check_text(d.content)

@app.post("/api/letters")
def create_letter(l: LetterIn, request: Request):
    throttle(f"letter:i:{_ip(request)}", 20, 3600)      # each attempt runs the filter, so cap how often one address can try
    if len(l.content.strip()) < 10:
        raise HTTPException(400, "A letter needs at least a few words.")
    if l.ambient_audio_choice not in AUDIO:
        raise HTTPException(400, "Unknown audio track.")
    if l.scheduled_date:
        try:
            if date.fromisoformat(l.scheduled_date) <= date.today():
                raise HTTPException(400, "Time-capsule dates must be in the future.")
        except ValueError:
            raise HTTPException(400, "Bad date.")
    verdict = ml_filter.check_text(l.content + " " + l.recipient)
    if not verdict["approved"]:
        # Blocked before it ever touches the database
        return JSONResponse(status_code=422, content={"approved": False, **verdict})
    user = auth.user_for(request.cookies.get(auth.COOKIE))
    with db.conn() as c:
        lid = c.execute(
            "INSERT INTO letters (recipient, content, author_token, user_id, scheduled_date, ambient_audio_choice) VALUES (?,?,?,?,?,?) RETURNING id",
            (l.recipient.strip(), l.content.strip(), l.author_token, user["id"] if user else None,
             l.scheduled_date or None, l.ambient_audio_choice)).fetchone()["id"]
    return {"approved": True, "id": lid}

@app.get("/api/letters")
def list_letters(request: Request, mine: str = ""):
    today = date.today().isoformat()
    user = auth.user_for(request.cookies.get(auth.COOKIE))
    with db.conn() as c:
        if mine:  # authors see their own sealed letters too
            if user:
                rows = c.execute("SELECT * FROM letters WHERE user_id=? OR author_token=? ORDER BY id DESC", (user["id"], mine)).fetchall()
            else:
                rows = c.execute("SELECT * FROM letters WHERE author_token=? ORDER BY id DESC", (mine,)).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM letters WHERE scheduled_date IS NULL OR scheduled_date <= ? ORDER BY id DESC LIMIT 100",
                (today,)).fetchall()
    out = []
    for r in rows:
        d = {k: r[k] for k in ("id", "recipient", "content", "timestamp", "scheduled_date", "echo_count", "ambient_audio_choice")}
        if d["scheduled_date"] and d["scheduled_date"] > today:
            d["locked"], d["content"] = True, ""   # never leak sealed text
        out.append(d)
    return out

@app.post("/api/letters/{letter_id}/echo")
def echo(letter_id: int, request: Request):
    throttle(f"echo:i:{_ip(request)}", 60, 3600)
    with db.conn() as c:
        c.execute("UPDATE letters SET echo_count = echo_count + 1 WHERE id=? AND (scheduled_date IS NULL OR scheduled_date <= ?)",
                  (letter_id, date.today().isoformat()))
        row = c.execute("SELECT echo_count FROM letters WHERE id=?", (letter_id,)).fetchone()
    if not row:
        raise HTTPException(404, "No such letter.")
    return {"echo_count": row["echo_count"]}

# ---------- the pages
if ON_VERCEL:
    @app.get("/", include_in_schema=False)
    def home():          # normally the CDN serves public/index.html before this is reached
        return RedirectResponse("/index.html")
else:                    # running locally: serve public/ ourselves
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "public"), html=True), name="site")
