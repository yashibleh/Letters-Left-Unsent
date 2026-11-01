"""Runs on Vercel after dependencies are installed and before deploying (see pyproject.toml).
Downloads the two small ONNX models into ./models so they ship inside the function. You can also run it locally."""
import sys
import ml_filter

try:
    ml_filter.download_models()
    print("[build] models ready")
except Exception as e:
    # Don't fail the whole deploy: the app can still fetch them into a temp folder on first use (slower).
    print(f"[build] WARNING: could not pre-download the models: {e}", file=sys.stderr)
