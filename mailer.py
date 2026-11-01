"""Sends email: Brevo's HTTPS API when BREVO_API_KEY is set (works on Vercel), else SMTP when SMTP_HOST is set,
else prints the message to the server log (handy for local tests).
Env: BREVO_API_KEY, MAIL_FROM (a sender address you verified in Brevo), MAIL_FROM_NAME,
     SMTP_HOST/PORT/USER/PASS/FROM, BASE_URL (your site's address, used inside the emailed links)."""
import config  # noqa: F401  (loads .env)
import json, os, smtplib, ssl, urllib.error, urllib.request
from email.message import EmailMessage

def base_url() -> str:
    b = os.getenv("BASE_URL")
    if b: return b.rstrip("/")
    prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    if prod: return "https://" + prod
    return "http://127.0.0.1:8000"

def mode() -> str:
    return "api" if os.getenv("BREVO_API_KEY") else "smtp" if os.getenv("SMTP_HOST") else "console"

def _brevo(to: str, subject: str, body: str) -> bool:
    payload = {"sender": {"name": os.getenv("MAIL_FROM_NAME", "Letters Left Unsent"), "email": os.getenv("MAIL_FROM") or os.getenv("SMTP_FROM", "")},
               "to": [{"email": to}], "subject": subject, "textContent": body}
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email", data=json.dumps(payload).encode(), method="POST",
        headers={"api-key": os.environ["BREVO_API_KEY"], "content-type": "application/json", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return 200 <= r.status < 300

def _smtp(to: str, subject: str, body: str) -> bool:
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER", ""); msg["To"], msg["Subject"] = to, subject
    msg.set_content(body)
    host, port = os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))
    user, pw = os.getenv("SMTP_USER"), os.getenv("SMTP_PASS")
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=15) as s:
            if user: s.login(user, pw or "")
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls(context=ssl.create_default_context())
            if user: s.login(user, pw or "")
            s.send_message(msg)
    return True

def send(to: str, subject: str, body: str) -> bool:
    """Never raises: a mail problem must not break a sign-up. Returns whether it was handed to a mail service."""
    m = mode()
    if m == "console":
        print("\n" + "=" * 64 + f"\n[EMAIL not configured - printing instead]\nTo: {to}\nSubject: {subject}\n\n{body}\n" + "=" * 64 + "\n", flush=True)
        return False
    try:
        return (_brevo if m == "api" else _smtp)(to, subject, body)
    except urllib.error.HTTPError as e:
        print(f"[EMAIL ERROR] {m} refused the message to {to}: {e.code} {e.read()[:300]!r}", flush=True)
        if e.code in (401, 403):
            print("[EMAIL HINT] Brevo blocks requests from IP addresses you haven't approved. If Brevo emailed you to authorise an IP, approve it; "
                  "or turn blocking off for API keys: Brevo > Settings > Security > Authorised IPs.", flush=True)
    except Exception as e:
        print(f"[EMAIL ERROR] could not send to {to}: {e}", flush=True)
    return False
