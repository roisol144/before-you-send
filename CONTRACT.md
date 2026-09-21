# Before You Send - Contract

Backend: FastAPI on port 8000, CORS open. Serves ../frontend statically at `/` (API routes take precedence). One command runs everything.

## GET /health
`{"status":"ok","mode":"laya"|"mock"}`

## POST /analyze
Request: `{"text": string}`  (empty/whitespace text -> neutral defaults, fight_risk 0, still 200)

Response:
```json
{
  "tone": {"label": "friendly|neutral|passive-aggressive|angry|anxious",
           "confidence": 0.0-1.0,
           "scores": {"friendly":0,"neutral":0,"passive-aggressive":0,"angry":0,"anxious":0}},
  "formality": {"score": 1.0-5.0, "confidence": 0.0-1.0 (optional)},
  "fight_risk": 0.0-1.0,
  "language": {"code": "en", "name": "English", "flag": "🇬🇧"},
  "latency_ms": 12.3,
  "mode": "laya|mock"
}
```
`scores` sums to ~1 over all five labels. `mode` is extra, informational.

Frontend rules: risk > 0.6 shows banner "Maybe sleep on it? 😬"; Copy & Send is green when fight_risk <= 0.35 (calm). Debounce ~150ms; abort stale requests. Fetch relative URL `/analyze`.

## Laya API (from README)
```python
from laya import Router
router = Router(preload=True)     # or laya.load("convaiinnovations/laya").predict(...)
state = {"message": text}
questions = {
  "tone":  {"type":"choice","instructions":"...","criteria":{"label":"description",...}},
  "formality": {"type":"score","instructions":"...","criteria":["level_0","level_1",...]},  # ordinal rubric, 5 levels
  "fight_risk": {"type":"noul","instructions":"..."}
}
result = router.predict(state, questions)
# result["answers"][key] = {"choice": label, "score": float, "noul": prob, "confidence": float}
# result["routing"] = {"model","repo","reason"}
```
Score is ordinal index (0-based float, e.g. 1.84) -> map to formality = clamp(score+1, 1, 5). Choice gives only the top label + confidence; distribute remaining mass across others for `scores`.

## Ownership
- backend/ : Backend agent (app.py, laya_engine.py, requirements.txt, tests). Mock via BYS_MOCK=1 or auto-fallback.
- frontend/ : Frontend agent (index.html, styles.css, app.js)
- README.md, run.sh, scripts/smoke_test.sh : Docs/QA agent. run.sh: creates venv, installs backend/requirements.txt, runs `uvicorn app:app --port 8000` from backend/ (honours BYS_MOCK).
