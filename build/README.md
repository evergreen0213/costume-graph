# 데이터 최신화

## 한 줄 실행

```bash
bash build/update.sh
```

수집 → 정제 → 그래프 → HTML 까지 한 번에 돌고 `costume-graph.html` 을 새로 씁니다.

## 파이프라인

| 단계 | 스크립트 | 입력 | 출력 |
|---|---|---|---|
| 1 | `fetch_new.py` | CrossRef + DBpia | `extra.json` |
| 2 | `prep.py` | `한국복식학회/excel/*.xls` + `extra.json` | `papers.json` |
| 3 | `graph.py` | `papers.json` | `graph.json` |
| 4 | `cluster.py` | `graph.json` | `graph.json` (+ `comm`/`fields`) |
| 5 | `render.py` | `template.html` + `graph.json` | `../costume-graph.html` |

`graph.py` 는 `graph.json` 을 통째로 다시 쓰면서 연구 갈래 정보(`comm`/`fields`)를 지운다.
그래서 3단계 뒤에는 **반드시** `cluster.py` 를 이어 돌려야 한다. `update.sh` 는 그렇게 돼 있다.
`cluster.py` 는 `networkx` 가 필요하다.

## fetch_new.py 가 하는 일

1. CrossRef 에서 『복식』(ISSN 1229-6880) 전체 DOI 목록을 받는다. 인증키 불필요.
2. `papers.json`(엑셀분) 과 `extra.json`(기수집분) 에 없는 DOI 만 골라낸다.
   대조 키는 (권, 호, 시작페이지) 와 정규화한 논문명.
3. 각 DOI 를 `doi.org` 로 따라가면 DBpia 상세 페이지가 나온다.
   그 페이지의 `citation_*` 메타 태그에서 **한글 논문명 · 한글 저자명 · 저자키워드**를 읽는다.
4. 엑셀과 같은 컬럼 모양으로 `extra.json` 에 **누적** 저장한다.
   이미 받은 논문은 다시 받지 않으므로 몇 번을 돌려도 안전하다.

키워드 원문은 `_keywords_raw` 에 남겨둔다. 정제 규칙을 고쳐도 재수집이 필요 없다.

## 한계

- **주저자 소속기관**: DBpia 메타에 없어 최신호는 `null`. 상세 패널의 소속 줄만 비어 보인다.
- **인용 횟수**: 0 으로 넣는다. 갓 나온 논문이라 어차피 0 이지만, 기존 논문의 인용수도
  엑셀 반출 시점(2026-02)에 멈춰 있다.
- **누락 가능성**: CrossRef 에 DOI 가 아직 등록되지 않은 논문은 잡히지 않는다.
  발행 직후보다 한 달쯤 뒤에 돌리는 편이 안전하다.

위 세 가지를 채우려면 KCI Open API 키가 필요하다.
`https://www.kci.go.kr/kciportal/po/openapi/openApiKeyRequest.kci` 에서 신청한다.
발급 후 호출 형태:

```
https://open.kci.go.kr/po/openapi/openApiSearch.kci
  ?apiCode=articleSearch&key=<키>&journal=복식&dateFrom=202601&dateTo=202612&displayCount=100
```

응답(XML)에 저자소속·키워드·인용수·권/호/페이지가 모두 들어 있어
`fetch_new.py` 의 수집부만 바꿔 끼우면 된다.

## 주기

『복식』은 격월간(연 6호)이다. 한 달에 한 번 정도 돌리면 충분하다.

```bash
# 매월 1일 오전 9시
0 9 1 * * bash build/update.sh >> build/update.log 2>&1
```
