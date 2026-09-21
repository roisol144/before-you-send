import sys
import types

import pytest
from fastapi.testclient import TestClient

import laya_engine
from app import app

client = TestClient(app)
LABELS = {"friendly", "neutral", "passive-aggressive", "angry", "anxious"}


def check_shape(d):
    assert d["tone"]["label"] in LABELS
    assert set(d["tone"]["scores"]) == LABELS
    assert abs(sum(d["tone"]["scores"].values()) - 1) < 0.02
    assert 1.0 <= d["formality"]["score"] <= 5.0
    assert 0.0 <= d["fight_risk"] <= 1.0
    assert {"code", "name", "flag"} <= set(d["language"])
    assert d["latency_ms"] >= 0 and d["mode"] in ("laya", "mock")


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("BYS_MOCK", "1")


def test_health_mock(mock_mode):
    assert client.get("/health").json() == {"status": "ok", "mode": "mock"}


def test_empty(mock_mode):
    d = client.post("/analyze", json={"text": "   "}).json()
    check_shape(d)
    assert d["fight_risk"] == 0 and d["mode"] == "mock"


def test_angry_vs_friendly(mock_mode):
    a = client.post("/analyze", json={"text": "You are USELESS!!! I hate this stupid mess"}).json()
    f = client.post("/analyze", json={"text": "Thanks so much, I really appreciate it! 😊"}).json()
    check_shape(a), check_shape(f)
    assert a["tone"]["label"] == "angry" and a["fight_risk"] > 0.6
    assert f["tone"]["label"] == "friendly" and f["fight_risk"] <= 0.35


def test_passive_aggressive(mock_mode):
    d = client.post("/analyze", json={"text": "As per my last email, fine. Whatever works."}).json()
    assert d["tone"]["label"] == "passive-aggressive"


@pytest.mark.parametrize("text,code", [
    ("שלום מה שלומך", "he"), ("مرحبا كيف حالك", "ar"), ("Привет, как дела?", "ru"),
    ("Hola, gracias por todo, estoy muy feliz", "es"), ("Bonjour, je suis très content de vous voir", "fr"),
    ("Hallo, ich bin nicht sicher und das ist sehr schwer", "de"), ("你好，谢谢", "zh"),
    ("こんにちは、ありがとう", "ja"), ("Hey, thanks for the help with this", "en"),
])
def test_languages(mock_mode, text, code):
    d = client.post("/analyze", json={"text": text}).json()
    assert d["language"]["code"] == code and d["language"]["flag"]


class FakeRouter:
    def __init__(self, preload=True):
        pass

    def predict(self, state, questions):
        assert set(questions) == {"tone", "formality", "fight_risk"}
        return {"answers": {
            "tone": {"choice": "angry", "confidence": 0.3, "probabilities": {"friendly": 0.05, "neutral": 0.1, "passive-aggressive": 0.15, "angry": 0.6, "anxious": 0.1}},
            "formality": {"score": 1.84, "confidence": 0.7},
            "fight_risk": {"noul": 0.9}}, "routing": {}}


def reset(monkeypatch):
    monkeypatch.delenv("BYS_MOCK", raising=False)
    monkeypatch.setattr(laya_engine, "_router", None)
    monkeypatch.setattr(laya_engine, "_failed", False)


def test_laya_mode_stubbed(monkeypatch):
    reset(monkeypatch)
    monkeypatch.setitem(sys.modules, "laya", types.SimpleNamespace(Router=FakeRouter))
    assert client.get("/health").json()["mode"] == "laya"
    d = client.post("/analyze", json={"text": "why would you do that"}).json()
    check_shape(d)
    assert d["mode"] == "laya" and d["tone"]["label"] == "angry"
    assert d["fight_risk"] == 0.9 and d["formality"]["score"] == 2.84


def test_fallback_on_import_failure(monkeypatch):
    reset(monkeypatch)
    monkeypatch.setitem(sys.modules, "laya", None)  # import raises ImportError
    assert client.get("/health").json()["mode"] == "mock"
    d = client.post("/analyze", json={"text": "hello there"}).json()
    check_shape(d)
    assert d["mode"] == "mock"


def test_fallback_on_predict_failure(monkeypatch):
    reset(monkeypatch)

    class Boom(FakeRouter):
        def predict(self, *a):
            raise RuntimeError("x")

    monkeypatch.setitem(sys.modules, "laya", types.SimpleNamespace(Router=Boom))
    d = client.post("/analyze", json={"text": "hello there"}).json()
    check_shape(d)
    assert d["mode"] == "mock"
