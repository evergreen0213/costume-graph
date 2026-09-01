#!/usr/bin/env bash
# 최신호 수집 -> 정제 -> 그래프 -> 군집 -> HTML 까지 한 번에
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ 1/5  최신호 수집 (CrossRef + DBpia)"
python3 build/fetch_new.py || echo "  (새 논문 없음 — 계속 진행)"

echo; echo "▶ 2/5  서지 정제"
python3 build/prep.py | tail -5

echo; echo "▶ 3/5  그래프 생성"
python3 build/graph.py

echo; echo "▶ 4/5  연구 갈래 군집"
# graph.py 가 graph.json 을 새로 쓰면서 comm/fields 를 날리므로 반드시 뒤이어 돌린다
python3 build/cluster.py

echo; echo "▶ 5/5  HTML 렌더"
python3 build/render.py

echo; echo "✔ 완료 — costume-graph.html"
