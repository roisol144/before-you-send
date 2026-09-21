#!/usr/bin/env bash
# Starts backend in mock mode, POSTs 4 samples, validates fields. PORT env (default 8000).
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8000}"
BASE="http://127.0.0.1:$PORT"
cd "$ROOT/backend" || exit 1
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
BYS_MOCK=1 "$PY" -m uvicorn app:app --host 127.0.0.1 --port "$PORT" >/tmp/bys_smoke.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null; wait $PID 2>/dev/null' EXIT
for i in $(seq 1 60); do
  curl -sf "$BASE/health" >/dev/null 2>&1 && break
  kill -0 $PID 2>/dev/null || { echo "server died"; cat /tmp/bys_smoke.log; exit 1; }
  sleep 0.5
done
curl -sf "$BASE/health" >/dev/null || { echo "health timeout"; cat /tmp/bys_smoke.log; exit 1; }
echo "health: $(curl -s "$BASE/health")"
FAIL=0
check() { # name text expected_lang
  local out
  out=$(curl -s -X POST "$BASE/analyze" -H 'Content-Type: application/json' \
    --data "$(NAME="$2" "$PY" -c 'import json,os;print(json.dumps({"text":os.environ["NAME"]}))')")
  RESP="$out" LABEL="$1" EXPECT="$3" "$PY" - <<'PY' || FAIL=1
import json, os, sys
try:
    d = json.loads(os.environ["RESP"])
    labels = {"friendly","neutral","passive-aggressive","angry","anxious"}
    assert d["tone"]["label"] in labels, "bad tone label"
    assert set(d["tone"]["scores"]) == labels, "scores keys"
    assert 0 <= d["tone"]["confidence"] <= 1, "confidence"
    assert 1 <= d["formality"]["score"] <= 5, "formality"
    assert 0 <= d["fight_risk"] <= 1, "fight_risk"
    for k in ("code", "name", "flag"):
        assert k in d["language"], "language." + k
    assert "latency_ms" in d, "latency_ms"
    exp = os.environ["EXPECT"]
    if exp:
        assert d["language"]["code"] == exp, "language %r != %r" % (d["language"]["code"], exp)
    print("PASS %-19s tone=%s(%.2f) formal=%.1f risk=%.2f lang=%s %.1fms" % (
        os.environ["LABEL"], d["tone"]["label"], d["tone"]["confidence"],
        d["formality"]["score"], d["fight_risk"], d["language"]["code"], d["latency_ms"]))
except Exception as e:
    print("FAIL %s: %s | %s" % (os.environ["LABEL"], e, os.environ["RESP"][:200]))
    sys.exit(1)
PY
}
check friendly "Thanks so much, this is wonderful! Really appreciate your help :)" en
check angry "This is completely unacceptable. I am sick of your excuses, fix it NOW!" en
check passive-aggressive "Per my last email, as I already mentioned, no worries if you can't be bothered." en
check hebrew "שלום, תודה רבה על העזרה, אני מעריך את זה מאוד" he
[ $FAIL -eq 0 ] && echo "SMOKE OK" || echo "SMOKE FAILED"
exit $FAIL
