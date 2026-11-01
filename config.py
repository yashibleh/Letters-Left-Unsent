"""Loads settings from a .env file next to the code (if there is one), so they survive closing the Command Prompt window.
Values you set in the window itself (set NAME=...) always win. Safe to import many times."""
import os
from pathlib import Path

def load():
    p = Path(__file__).parent / ".env"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():     # utf-8-sig: Notepad may add an invisible marker
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        os.environ.setdefault(k.strip(), v)

load()
