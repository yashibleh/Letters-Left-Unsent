# 📜 Letters Left Unsent

> *ATLAS OF UNSENT WORDS // PUBLIC SANCTUARY & VISUAL ARCHIVE*

**What is this website?** 
Have you ever written a message you couldn't bring yourself to send? A final goodbye, a quiet thank you, or a confession you had to keep to yourself? **Letters Left Unsent** is a secure, anonymous space to drop those unspoken words. It is a digital sanctuary for gratitude and affection, where your letters will never be delivered to their recipients, but instead stored in a beautifully designed, purely positive public archive for the world to witness. 

## ✨ Core Features

* **The Sunlit Threshold (`index.html`):** Instead of dropping visitors straight into a feed, the journey begins with a short, cinematic welcoming sequence—an interactive typewriter path bathed in golden-hour light and drifting dust motes that sets a reflective tone.

* **The Compassion Guardian (ML Moderation Pipeline):** Every submission passes through a real-time Natural Language Processing (NLP) interceptor before reaching the database. If negative, spiteful, or political themes are detected, a gentle archival dialog nudges the writer: *"This space is for healing and hope. We noticed some negative themes in your draft. Want to try focusing on a positive memory instead?"*

* **Ambient Soundscapes:** Writers can pair their letters with subtle background audio (rain on a window, vinyl crackle, autumn wind, or night hum) that plays softly when a stranger reads their entry.

* **Time-Capsule Drops:** Schedule letters to remain sealed in the archive until a specific future milestone or anniversary date before illuminating on the public wall.

* **The "Echo" Button:** Instead of vanity likes or public comment sections, readers can gently "Echo" a letter that brought them comfort, incrementing a quiet resonance counter for the original author.

* **Personal Drawer:** Users can revisit their own history of pinned and scheduled letters alongside the global public wall.

## 🎨 Aesthetic & Design System

Designed with an **Atlas Archive** editorial structure, the UI intentionally rejects sterile, generic modern web tropes (no neon gradients or glassmorphism) in favor of a tactile, human-crafted ledger:

* **Color Palette:**
  * `Oatmeal Linen (#dfd9cc)` & `Sheer Lace Cream (#f6f1e5)` for paper surfaces.
  * `Mahogany Shadow (#231b15)` for sharp architectural ink borders and brutalist offset shadows.
  * `Autumn Terracotta (#c86d44)`, `Meadow Olive (#4a5842)`, and `2000s Sunflare Gold (#d89634)` for warm, nostalgic accents.

* **Typography:** High-contrast editorial serifs (`Cormorant Garamond`), catalog metadata monospaced type (`Space Mono` & `Special Elite`), and organic handwriting (`Caveat`).

* **Tactile Details:** SVG analog film-grain overlay, dappled window-blind light rays, lined stationery with red margin rules, and masking tape strips.

## 🧠 Machine Learning Moderation Pipeline

To preserve the platform as an emotional refuge while maintaining blazing-fast performance and a tiny server footprint, the backend runs a heavily optimized two-stage NLP check using quantized `int8` ONNX models:

1. **Zero-Shot Topic Classification (`deberta-v3-xsmall-zeroshot-v1.1-all-33`):**
   Weighing in at just 87 MB (down from BART's 1.6 GB), this model evaluates the draft against custom target labels (`["gratitude", "affection", "politics", "controversial debate", "gossip"]`). It successfully blocks political or debate-heavy submissions without requiring custom dataset training.

2. **Toxicity & Spite Detection (`Xenova/toxic-bert`):**
   An optimized 111 MB ONNX copy of the model powering Detoxify. It analyzes syntax and sentiment in real-time to catch toxicity, severe toxicity, insults, and passive-aggressive phrasing before they ever hit the database.

### Moderation Workflow

```text
[User Submits Draft] 
       │
       ▼
[Backend API] ──► Runs deberta-v3-xsmall-zeroshot (Topic Check)
       │      ──► Runs Xenova/toxic-bert (Toxicity & Spite Check)
       ▼
  Pass Both Checks?
   ├── YES ──► Saved to SQLite DB ──► Pinned to Public Wall / Scheduled
   └── NO  ──► Blocked from DB    ──► Triggers "Compassion Guardian" UI Dialog
```

## 🛠️ Tech Stack

* **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS, Custom CSS3 (Film grain, CSS grid ledger, keyframe animations)
* **Backend:** Python (FastAPI / Flask)
* **Machine Learning:** Hugging Face `transformers` / `onnxruntime` (`deberta-v3-xsmall-zeroshot` & `Xenova/toxic-bert`)
* **Database:** SQLite3

## 📂 Project Structure

```text
letters-left-unsent/
├── index.html          # Welcoming onboarding path ("The Sunlit Attic Path")
├── app.html            # Main workspace: Atlas header, writing desk, public wall & drawer
├── css/
│   └── style.css       # Custom nostalgic palette, paper textures, and brutalist ledger rules
├── js/
│   ├── app.js          # Frontend state, API calls, tab switching, and ML popup triggers
│   └── audio.js        # Web Audio / ambient soundscape controller
├── backend/            # Python server & ML pipeline
│   ├── main.py         # API endpoints (POST /letters, GET /letters, POST /echo)
│   ├── moderator.py    # ONNX inference logic for DeBERTa and Toxic-BERT
│   └── database.db     # SQLite storage for letters, timestamps, and echo counts
└── README.md
```



## 📜 Philosophy

*Nothing here is ever sent to anyone. Only warm words are pinned to this wall.*
