"""Two-layer text filter on ONNX Runtime. No PyTorch, no transformers.

  Layer 1  toxicity   Xenova/toxic-bert (ONNX, int8, ~111 MB)  - insults, threats, obscenity, hate
  Layer 2  topics     MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33 (ONNX, int8, ~13 MB)
                      - zero-shot labels: politics, controversy, gossip

The models (~125 MB) are downloaded by build.py at deploy time, or on first use if missing. Settings (all optional environment variables):
  TOPIC_THRESHOLD (0.80)  THRESH_POLITICS / THRESH_CONTROVERSY / THRESH_GOSSIP  per-topic override
  TOXIC_THRESHOLD (0.55)  ORT_THREADS (default: your CPU cores, split between the two models)  FILTER_PARALLEL=0 to run them one after the other
  MODELS_DIR
  ZS_REPO, ZS_ONNX, TOX_REPO, TOX_ONNX  swap models. More accurate but bigger topic model (needs Vercel "large functions"):
      ZS_REPO=MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33   (adds ~80 MB)
  MOCK_ML=1  keyword stub for quick UI tests
"""
import config  # noqa: F401  (loads .env)
import json, os, re, shutil, tempfile, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

MODELS = Path(os.getenv("MODELS_DIR") or Path(__file__).parent / "models")
TMP_MODELS = Path(tempfile.gettempdir()) / "letters-models"   # writable fallback when the deployed folder is read-only
ZS_REPO = os.getenv("ZS_REPO", "MoritzLaurer/xtremedistil-l6-h256-zeroshot-v1.1-all-33")
ZS_ONNX = os.getenv("ZS_ONNX", "onnx/model_quantized.onnx")
TOX_REPO = os.getenv("TOX_REPO", "Xenova/toxic-bert")
TOX_ONNX = os.getenv("TOX_ONNX", "onnx/model_quantized.onnx")

TOPICS = {  # reason code -> how the label is worded for the model
    "politics": "politics or government",
    "controversy": "a controversial debate or argument",
    "gossip": "gossip or complaints about another person",
}
TEMPLATE = "This example is about {}"
TOPIC_THRESHOLD = float(os.getenv("TOPIC_THRESHOLD", "0.80"))
TOXIC_THRESHOLD = float(os.getenv("TOXIC_THRESHOLD", "0.55"))
TOX_DEFAULT_NAMES = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

# Speed: with 4+ CPU cores the two models run side by side, each on half the cores; otherwise one after the other,
# skipping the topic check when the toxicity check has already said no. Vercel gives each function 1 core.
CORES = os.cpu_count() or 2
PARALLEL = not os.getenv("VERCEL") and CORES >= 4 and os.getenv("FILTER_PARALLEL", "1") == "1"

def _threads() -> int:
    if os.getenv("ORT_THREADS"):
        return max(1, int(os.getenv("ORT_THREADS")))
    if os.getenv("VERCEL"):
        return 1
    return max(1, CORES // 2) if PARALLEL else min(4, CORES)

_zs = _tox = None
_lock = threading.Lock()

def _topic_threshold(topic: str) -> float:
    return float(os.getenv("THRESH_" + topic.upper(), TOPIC_THRESHOLD))

# ---------------------------------------------------------------- model files
def _complete(folder: Path, need) -> bool:
    return all((folder / f).exists() and (folder / f).stat().st_size > 0 for f in need)

def _download(repo: str, filename: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)          # raises OSError on a read-only folder
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    part = dest.with_name(dest.name + ".part")
    print(f"[filter] downloading {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "letters-left-unsent/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as out:
        shutil.copyfileobj(r, out, 1024 * 1024)
    if filename.endswith(".onnx") and part.stat().st_size < 1_000_000:
        part.unlink()
        raise RuntimeError(f"{url} did not return a model file")
    part.replace(dest)

def _ensure(repo: str, onnx_name: str) -> Path:
    need = ["config.json", "tokenizer.json", onnx_name]
    name = repo.replace("/", "__")
    bases = [MODELS, TMP_MODELS]
    for base in bases:
        if _complete(base / name, need):
            return base / name
    last = None
    for base in bases:
        try:
            for f in need:
                _download(repo, f, base / name / f)
            return base / name
        except OSError as e:
            last = e
    raise RuntimeError(f"Could not get the model files for {repo}: {last}")

def download_models():
    """Used by build.py so the files ship inside the deployment."""
    _ensure(TOX_REPO, TOX_ONNX)
    _ensure(ZS_REPO, ZS_ONNX)

class _Model:
    def __init__(self, repo: str, onnx_name: str):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        folder = _ensure(repo, onnx_name)
        cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        self.id2label = {int(k): v for k, v in cfg["id2label"].items()}
        self.tok = Tokenizer.from_file(str(folder / "tokenizer.json"))
        self.tok.enable_truncation(max_length=min(512, cfg.get("max_position_embeddings", 512)), strategy="only_first")
        self.tok.enable_padding(pad_id=cfg.get("pad_token_id", 0), pad_token="[PAD]")
        so = ort.SessionOptions()
        so.intra_op_num_threads = _threads(); so.inter_op_num_threads = 1
        so.enable_cpu_mem_arena = False          # keeps memory flat on small servers
        self.sess = ort.InferenceSession(str(folder / onnx_name), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}

    def logits(self, items, batch: int = 8) -> np.ndarray:
        """items: list of strings, or of (premise, hypothesis) pairs. Returns raw model outputs."""
        out = []
        for i in range(0, len(items), batch):
            enc = self.tok.encode_batch(items[i:i + batch])
            feed = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                    "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                    "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64)}
            out.append(self.sess.run(None, {k: v for k, v in feed.items() if k in self.inputs})[0])
        return np.concatenate(out, axis=0)

def load_models():
    global _zs, _tox
    if _mock_on():
        return
    with _lock:
        if _tox is None:
            _tox = _Model(TOX_REPO, TOX_ONNX)
        if _zs is None:
            _zs = _Model(ZS_REPO, ZS_ONNX)

# ---------------------------------------------------------------- maths
def _sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

def _entail_prob(model: _Model, logits: np.ndarray) -> np.ndarray:
    """Probability of 'entailment' for each (text, label) pair, ignoring the neutral class like the HF pipeline does."""
    names = {i: n.lower() for i, n in model.id2label.items()}
    e = next(i for i, n in names.items() if n.startswith("entail"))
    c = next((i for i, n in names.items() if n.startswith("contra")), None)
    if c is None:
        c = next(i for i in names if i != e)       # two-class models call it "not_entailment"
    pair = logits[:, [c, e]]
    pair = pair - pair.max(axis=1, keepdims=True)
    ex = np.exp(pair)
    return ex[:, 1] / ex.sum(axis=1)

def _chunks(text: str, size: int = 700, max_chunks: int = 6):
    """Long letters are checked in pieces so nothing past the model's window slips through."""
    text = " ".join(text.split())
    if len(text) <= size:
        return [text]
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        while len(sent) > size:
            if cur: out.append(cur); cur = ""
            out.append(sent[:size]); sent = sent[size:]
        if cur and len(cur) + len(sent) + 1 > size:
            out.append(cur); cur = sent
        else:
            cur = (cur + " " + sent).strip()
    if cur: out.append(cur)
    return out[:max_chunks]

# ---------------------------------------------------------------- the check
def _mock_on(): return os.getenv("MOCK_ML") == "1"

def _mock(text):
    t = text.lower()
    bad = ["hate", "idiot", "stupid", "election", "government", "trump", "modi", "gossip", "slut", "loser"]
    hit = [w for w in bad if w in t]
    return {"approved": not hit, "reasons": ["mock"] if hit else [], "scores": {}}

def _tox_scores(chunks) -> dict:
    probs = _sigmoid(_tox.logits(chunks)).max(axis=0)
    out = {}
    for i, p in enumerate(probs):
        name = _tox.id2label.get(i, "")
        if name.startswith("LABEL_") or not name:
            name = TOX_DEFAULT_NAMES[i] if i < len(TOX_DEFAULT_NAMES) else f"toxic_{i}"
        out[name] = float(p)
    return out

def _topic_scores(chunks) -> dict:
    pairs = [(c, TEMPLATE.format(label)) for c in chunks for label in TOPICS.values()]
    probs = _entail_prob(_zs, _zs.logits(pairs)).reshape(len(chunks), len(TOPICS)).max(axis=0)
    return {topic: float(p) for topic, p in zip(TOPICS, probs)}

def check_text(text: str, full: bool = False) -> dict:
    """full=True always scores every label (used by test_filter.py). Otherwise, when the models run one after the other,
    the topic check is skipped if the toxicity check has already rejected the text."""
    if _mock_on():
        return _mock(text)
    load_models()
    t0 = time.perf_counter()
    chunks = _chunks(text)
    with _lock:
        if PARALLEL:
            with ThreadPoolExecutor(max_workers=2) as ex:
                f_tox, f_top = ex.submit(_tox_scores, chunks), ex.submit(_topic_scores, chunks)
                tox, topics = f_tox.result(), f_top.result()
        else:
            tox = _tox_scores(chunks)
            topics = _topic_scores(chunks) if (full or not any(p >= TOXIC_THRESHOLD for p in tox.values())) else {}
    scores, reasons = {}, []
    for name, p in tox.items():
        scores[name] = round(p, 3)
        if p >= TOXIC_THRESHOLD:
            reasons.append(name)
    for topic, p in topics.items():
        scores[topic] = round(p, 3)
        if p >= _topic_threshold(topic):
            reasons.append(topic)
    print(f"[filter] read {len(chunks)} piece(s) in {(time.perf_counter() - t0) * 1000:.0f} ms ({'side by side' if PARALLEL else 'one after the other'})", flush=True)
    return {"approved": not reasons, "reasons": sorted(set(reasons)), "scores": scores}
