"""Laya Router wrapper with lazy load and automatic fallback to mock."""
import os
import threading
import time

import mock_engine
from mock_engine import LABELS, detect_language

QUESTIONS = {
    "tone": {"type": "choice",
             "instructions": "Classify the emotional tone of this message.",
             "criteria": {
                 "friendly": "warm, kind, positive",
                 "neutral": "matter-of-fact, no strong emotion",
                 "passive-aggressive": "indirectly hostile, sarcastic or icy politeness",
                 "angry": "openly hostile, aggressive or insulting",
                 "anxious": "worried, apologetic, uncertain"}},
    "formality": {"type": "score",
                  "instructions": "Rate the formality of this message.",
                  "criteria": ["very informal slang", "informal", "neutral", "formal", "very formal"]},
    "fight_risk": {"type": "noul",
                   "instructions": "Is this message likely to start a fight or hurt the relationship if sent?"},
}

_router = None
_failed = False
_lock = threading.Lock()
_predict_lock = threading.Lock()  # one GPU/MPS inference at a time


def _load():
    global _router, _failed
    with _lock:  # concurrent first requests must not each load the model
        if _router is not None or _failed:
            return _router
        try:
            from laya import Router
            _router = Router(preload=True)
        except Exception:
            _failed = True
            _router = None
        return _router


def warmup():
    """Load the model once at startup so the first keystroke isn't slow."""
    if not mock_forced():
        _load()


def mock_forced():
    return os.environ.get("BYS_MOCK", "") not in ("", "0", "false")


def mode():
    """Current mode; tries to load Laya lazily unless forced mock."""
    if mock_forced():
        return "mock"
    return "laya" if _load() is not None else "mock"


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _laya(router, text):
    with _predict_lock:
        res = router.predict({"message": text}, QUESTIONS)
    a = res["answers"]
    probs = a["tone"].get("probabilities") or {}
    scores = {l: float(probs.get(l, 0.0)) for l in LABELS}
    total = sum(scores.values()) or 1.0
    scores = {l: v / total for l, v in scores.items()}
    label = max(scores, key=scores.get) if probs else "neutral"
    conf = _clamp(scores[label], 0.0, 1.0)
    f = a["formality"]
    out = {
        "tone": {"label": label, "confidence": round(conf, 3), "scores": {k: round(v, 4) for k, v in scores.items()}},
        "formality": {"score": round(_clamp(float(f.get("score", 2.0)) + 1, 1.0, 5.0), 2)},
        "fight_risk": round(_clamp(float(a["fight_risk"].get("noul", 0.0)), 0.0, 1.0), 3),
        "language": detect_language(text),
    }
    if f.get("confidence") is not None:
        out["formality"]["confidence"] = _clamp(float(f["confidence"]), 0.0, 1.0)
    return out


def analyze(text):
    t0 = time.perf_counter()
    result, used = None, "mock"
    if not mock_forced() and text.strip():
        router = _load()
        if router is not None:
            try:
                result, used = _laya(router, text), "laya"
            except Exception:
                result = None
    elif not mock_forced():
        used = "laya" if _load() is not None else "mock"
    if result is None:
        result = mock_engine.analyze(text)
    result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    result["mode"] = used
    return result
