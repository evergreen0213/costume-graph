#!/usr/bin/env bash
# 최신호 수집 -> 정제 -> 도상 -> 화면 데이터 -> HTML -> 연기 시험 까지 한 번에
#
#   bash build/update.sh              1안(조각보)만 짓는다. CI 가 쓰는 기본값
#   DESIGN=hyungbae bash …            다른 안 하나만
#   DESIGN=all      bash …            아홉 안 모두 (디자인 고르는 동안 쓰는 용도)
set -euo pipefail
cd "$(dirname "$0")/.."

# 파이썬은 프로세스마다 문자열 해시를 무작위화한다. viewdata.py 가 키워드 문자열 set 을
# 그래프에 넣으므로 노드 순서가 흔들리면 louvain seed 를 고정해도 군집이 달라진다.
# viewdata.py 자체가 정렬로 막고 있지만, 매달 자동으로 도는 파이프라인이라 이중으로 건다.
export PYTHONHASHSEED=0

ALL='bojagi hyungbae chaekgado saekdong hanbok tal wanja mugunghwa hanok'
DESIGNS="${DESIGN:-bojagi}"
[ "$DESIGNS" = all ] && DESIGNS="$ALL"

# 안 이름 -> 산출물 파일명 (render.py 의 SUFFIX 와 같아야 한다)
outfile() {
  case "$1" in
    bojagi)    echo 'costume-graph.html' ;;
    hyungbae)  echo 'costume-graph-2-hyungbae.html' ;;
    chaekgado) echo 'costume-graph-3-chaekgado.html' ;;
    saekdong)  echo 'costume-graph-4-saekdong.html' ;;
    hanbok)    echo 'costume-graph-5-hanbok.html' ;;
    tal)       echo 'costume-graph-6-tal.html' ;;
    wanja)     echo 'costume-graph-7-wanja.html' ;;
    mugunghwa) echo 'costume-graph-8-mugunghwa.html' ;;
    hanok)     echo 'costume-graph-9-hanok.html' ;;
    *) echo "모르는 디자인: $1" >&2; return 1 ;;
  esac
}
for d in $DESIGNS; do outfile "$d" >/dev/null; done   # 오타면 여기서 먼저 멈춘다

echo "▶ 1/5  최신호 수집 (CrossRef + DBpia)"
# 예전에는 어떤 실패든 '새 논문 없음' 으로 뭉개고 넘어갔다. 그러면 DBpia 쪽이 바뀌어
# 수집이 멎어도 로그를 들여다보지 않는 한 몇 달을 모른 채 지나간다. 이제는 가른다.
set +e; python3 build/fetch_new.py; rc=$?; set -e
case "$rc" in
  0) ;;                                   # 정상 — 새 논문이 없었거나 받아 왔거나
  2) echo "::error::새 논문을 찾았는데 상세를 하나도 받지 못했다. DBpia 메타 확인 필요"
     exit 1 ;;                            # 여기서 멈춘다 → Actions 가 메일로 알린다
  *) echo "::warning::최신호 수집이 실패했다(종료코드 $rc). 기존 자료로 계속한다." ;;
esac

echo; echo "▶ 2/5  서지 정제"
python3 build/prep.py | tail -5

echo; echo "▶ 3/5  복식 도상 생성"
# papers.json 과 무관하고 결정적이지만, glyphs.py 를 고쳤는데 glyphs.json 이
# 낡아 있는 사고를 막으려고 항상 다시 만든다.
python3 build/glyphs.py

echo; echo "▶ 4/5  화면 데이터 + HTML  [$DESIGNS]"
for d in $DESIGNS; do
  python3 build/viewdata.py --design "$d" | tail -1
  python3 build/render.py   --design "$d"
done

echo; echo "▶ 5/5  연기 시험"
# 문법이 멀쩡해도 초기화 중에 죽는 페이지가 있다. node --check 로는 못 잡는다.
# 선언 전 참조 한 줄 때문에 버튼이 죽은 페이지가 나간 적이 있어 배포 직전 관문으로 둔다.
for d in $DESIGNS; do
  f=$(outfile "$d")
  echo "  · $f"
  node build/smoke.js "$f" | tail -2
done

echo; echo "✔ 완료 — $(for d in $DESIGNS; do outfile "$d"; done | tr '\n' ' ')"
