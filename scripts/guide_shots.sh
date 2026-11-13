#!/usr/bin/env bash
# Take numbered screenshots of every page for the user guide (Microsoft Edge headless).
# Usage: bash scripts/guide_shots.sh [base_url]   (default: local preview server)
# Written with the help of an SI coding assistant (Claude Code).
BASE="${1:-http://localhost:8765/}"
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
OUT="$(cd "$(dirname "$0")/.." && pwd)/report/shots"
mkdir -p "$OUT"
shot() { # name url width height
  "$EDGE" --headless=new --enable-webgl --ignore-gpu-blocklist --use-gl=angle --use-angle=swiftshader-webgl --enable-unsafe-swiftshader --hide-scrollbars --no-first-run --user-data-dir="$OUT/../.edge-profile" \
    --window-size="$3,$4" --virtual-time-budget=40000 --screenshot="$(cygpath -w "$OUT/$1.png")" "$2" >/dev/null 2>&1
  echo "$1: $(stat -c %s "$OUT/$1.png" 2>/dev/null || echo missing)"
}
Q="area=evia&from=2003&to=2025&month=2007-08&mode=abs&guide=1"
shot home          "${BASE}?area=greece&guide=1"                1280 1500
shot calendar      "${BASE}calendar/?${Q}&detail=1"             1280 3600
shot alerts        "${BASE}alerts/?guide=1"                     1280 2000
shot live          "${BASE}live/?area=greece&guide=1"           1280 1900
shot how           "${BASE}how-it-works/?guide=1"               1280 1500
shot validation    "${BASE}validation/?guide=1"                 1280 3400
shot limits        "${BASE}limits/?guide=1"                     1280 1100
shot credits       "${BASE}credits/?guide=1"                    1280 1900
shot home_harm     "${BASE}?area=greece&hero=harm"                      1280 1000
shot mobile_detail "${BASE}calendar/?area=evia&from=2003&to=2025&month=2007-08&mode=abs&detail=1" 390 1400
shot anomaly       "${BASE}calendar/?area=greece&from=2003&to=2025&month=2007-08&mode=anomaly" 1280 2200
