#!/usr/bin/env bash
# Usage: ./run.sh [--laya]   (BYS_MOCK=1 forces mock mode; PORT overrides port)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
LAYA=0
for a in "$@"; do [ "$a" = "--laya" ] && LAYA=1; done
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
if [ "$LAYA" = 1 ]; then pip install -q laya; fi
echo "Before You Send -> http://localhost:${PORT:-8000} (BYS_MOCK=${BYS_MOCK:-unset})"
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"
