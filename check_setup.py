"""Run this on your own computer BEFORE deploying:   python check_setup.py
Set DATABASE_URL first to test your Neon database (Windows cmd:  set DATABASE_URL=postgresql://...)."""
import os, time, traceback

def step(title, fn):
    print(f"\n== {title}")
    try:
        fn(); print("   OK")
        return True
    except Exception:
        print("   FAILED"); traceback.print_exc(limit=2); return False

def database():
    import database as db
    print("   backend:", "Postgres (Neon)" if db.POSTGRES else "SQLite file (set DATABASE_URL to test Neon)")
    key = f"_check_{int(time.time())}"
    with db.conn() as c:
        c.execute("INSERT INTO attempts VALUES (?,?)", (key, int(time.time())))
        n = c.execute("SELECT COUNT(*) AS n FROM attempts WHERE key=?", (key,)).fetchone()["n"]
        c.execute("DELETE FROM attempts WHERE key=?", (key,))
    assert n == 1, "wrote a row but did not read it back"
    with db.conn() as c:
        for t in ("letters", "users", "sessions", "tokens", "attempts"):
            c.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchall()
    print("   tables present, write/read/delete works")

def models():
    import ml_filter
    t = time.time(); ml_filter.load_models(); print(f"   models loaded in {time.time() - t:.1f}s")
    for text in ("Thank you for always believing in me.", "You are a stupid idiot and I hate you."):
        t = time.time(); r = ml_filter.check_text(text); print(f"   {'pinned ' if r['approved'] else 'blocked'} ({(time.time() - t) * 1000:.0f} ms) {text!r}")

def email():
    import mailer
    print("   mode:", {"api": "Brevo API", "smtp": "SMTP", "console": "NOT CONFIGURED - links will only appear in the server log"}[mailer.mode()])
    print("   links will point to:", mailer.base_url())
    if mailer.mode() == "api" and not os.getenv("MAIL_FROM"):
        raise RuntimeError("BREVO_API_KEY is set but MAIL_FROM (your verified sender address) is not")

if __name__ == "__main__":
    results = [step("Database", database), step("Filter models", models), step("Email settings", email)]
    print("\nAll good - ready to deploy." if all(results) else "\nFix the failed step(s) above, then run this again.")
