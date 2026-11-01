# Letters Left Unsent - Vercel version

Runs on Vercel (free Hobby plan) with a free Neon Postgres database and Brevo for email.
Your original project is untouched; this is a separate copy.

## Layout
- `main.py`  the FastAPI app (Vercel finds it automatically)      - `public/`  the website (served by Vercel's CDN)
- `database.py`, `auth.py`, `ratelimit.py`, `mailer.py`, `ml_filter.py`  backend modules
- `build.py` downloads the two ONNX models at deploy time (see `pyproject.toml`)
- `check_setup.py` run it locally before deploying;  `test_filter.py` try the filter on sample letters

## Setup, in order
1. **Neon** (neon.tech, free, no card): create a project in the **Singapore** region (the closest to India). Copy the *pooled* connection string
   (host contains `-pooler`). It looks like `postgresql://user:pass@ep-...-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
2. **Brevo** (brevo.com, free: 300 emails/day, no card): create an account, add and verify a sender address (Senders), then create an API key
   (SMTP & API -> API keys).
3. **Settings file:** `copy .env.example .env`, then `notepad .env` and fill in the values (Notepad must save it as `.env`, not `.env.txt`).
   The app reads it on every start, so it always uses the same database.
   **Try it locally** (Command Prompt, from this folder, using `python -m` for everything):
   ```
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python check_setup.py
   python -m uvicorn main:app
   ```
   Open http://127.0.0.1:8000 and test sign-up, the email link, writing a letter.
4. **Deploy.** Either (a) push this folder to a GitHub repository and import it at vercel.com/new, or (b) install Node.js, run
   `npm install -g vercel`, then `vercel` and `vercel --prod` from this folder.
   Do NOT set a Build Command in Vercel's settings (that would override `build.py`).
5. In the Vercel project: **Settings -> Environment Variables**, add `DATABASE_URL`, `BREVO_API_KEY`, `MAIL_FROM`, `MAIL_FROM_NAME`
   and `BASE_URL` (your site address, e.g. `https://your-project.vercel.app`). Then redeploy so they take effect.
6. Visit your site, sign up, confirm the email, write a letter.

## Notes
- No persistent disk on Vercel: everything lives in Neon. Your old local `letters.db` is not copied over.
- Cold starts: the first request after a quiet spell loads both models (a few seconds).
- Emails not arriving? Check Brevo's logs, your spam folder, and that MAIL_FROM is a verified sender.
- Vercel's free Hobby plan is meant for personal, non-commercial use.

## Brevo and IP addresses
Brevo blocks API calls from IP addresses you haven't approved and emails you to authorise each new one.
Your home IP can change, and Vercel's outgoing IPs are not fixed, so before deploying turn the blocking off for API keys:
Brevo > Settings > Security > Authorised IPs > deactivate blocking. Keep the API key secret; regenerate it if it ever leaks.

## If the wall or drawer looks empty
Open http://127.0.0.1:8000/api/health - it says `postgres` or `sqlite`. If that isn't what you expect, your settings
weren't loaded (check `.env`). The server window also prints `[db] using ...` when it starts.
