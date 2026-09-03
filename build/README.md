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
| 3 | `glyphs.py` | (없음) | `glyphs.json` |
| 4 | `viewdata.py --design D` | `papers.json` + `glyphs.json` + `designs.py` | `view-D.json` |
| 5 | `render.py --design D` | `template.html` + `view-D.json` | `../costume-graph[-N-D].html` |
| 6 | `smoke.js <파일>` | 완성된 html | 통과/실패 (배포 직전 관문) |

### 디자인 안

지금 아홉 안이 있다 — 조각보 `bojagi` · 흉배 `hyungbae` · 책가도 `chaekgado` ·
색동 고리 `saekdong` · 한복 `hanbok` · 하회탈 `tal` · 완자창 `wanja` ·
무궁화 `mugunghwa` · 한옥 `hanok`. 산출물 이름은 `render.py` 의 `SUFFIX` 와
`update.sh` 의 `outfile()` 두 곳이 같아야 한다.

`designs.py` 가 안마다 테두리·구역·장식 셋만 바꾼다. 키워드 추출·군집·이름·도상·
논문/저자 상세는 전부 공통이고 `template.html` 도 하나다.

```bash
bash build/update.sh              # 1안(조각보)만. CI 가 쓰는 기본값
DESIGN=hyungbae bash build/update.sh
DESIGN=all      bash build/update.sh   # 아홉 안 모두 — 고르는 동안 쓰는 용도
```

**CI 는 기본값으로 한 안만 짓는다.** Pages 에 파일이 여럿 올라가면 학회에
어느 주소를 줄지 혼선이 생긴다. 안이 확정되면 `update.sh` 의 `DESIGN` 기본값
한 줄만 바꾸면 된다.

`viewdata.py` 는 화면이 실제로 쓰는 모양을 낸다 — 키워드 동시출현 지도(노드·간선·연구
갈래·갈래 자리)와 키워드를 눌렀을 때 나올 논문/저자 상세층까지 `view.json` 한 파일에 담는다.
`networkx` · `numpy` · `scipy` · `shapely` · `matplotlib` 이 필요하다. matplotlib 은
그리기용이 아니라 `Path.contains_points` 로 한반도 안팎을 판정하는 데만 쓴다.

한반도 윤곽 좌표는 `korea.py` 에 값으로 박혀 있고, `glyphs.py` 는 `math` 만 쓴다.
**빌드 중에는 어떤 네트워크 접근도 없다** (최신호를 받아오는 1단계 `fetch_new.py` 만 예외).

`glyphs.json` 은 `papers.json` 과 무관하고 결정적이라 매번 만들 필요는 없지만,
`glyphs.py` 를 고쳤는데 `glyphs.json` 이 낡아 있는 사고를 막으려고 항상 다시 만든다.

`audit.py` 는 파이프라인에 들어가지 않는다. 갈래 분리가 통계적으로 타당한지
사람이 가끔 확인하는 용도다 (모듈러리티, 무작위 배정 대비 편차, 잘못 놓인 키워드 비율).

`smoke.js` 는 최소한의 DOM 을 흉내 내어 페이지 스크립트를 통째로 실행해 본다. `node` 만
있으면 되고 브라우저는 필요 없다. 문법은 멀쩡한데 초기화 중에 죽는 페이지(선언 전 참조,
없는 id 참조 등)를 잡는다 — `node --check` 로는 못 잡는 종류다. 실제로 그런 한 줄 때문에
버튼이 죽은 페이지가 나간 적이 있어 배포 직전 관문으로 뒀다. 실패하면 종료코드 1 이라
파이프라인이 거기서 멈추고 Pages 배포까지 가지 않는다.

논문 한 편이 키워드 2개·저자 1.5명에만 붙어서 논문까지 노드로 올린 그래프는 군집 구조가
너무 약했다(털뭉치). 키워드 동시출현으로 바꾸면서 모듈러리티가 0.705 로 올라갔고,
논문은 지도에서 내려 상세층으로 옮겼다. 이전의 `graph.py`/`cluster.py`/`cograph.py` 는
`viewdata.py` 로 대체되어 지웠다 (필요하면 git 이력에서 되살릴 수 있다).

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

『복식』은 격월간(연 6호)이고 발행일이 짝수달 말일(2/28·4/30·…·12/31)인데
실제 발행은 다음 달까지 밀리기도 한다. 그래서 쫓아가지 않고, 다음 발행월 1일에
지난 호를 줍는다.

```bash
# 짝수달 1일 오전 9시 — 지난 호를 넉넉히 줍는다
0 9 1 2,4,6,8,10,12 * bash build/update.sh >> build/update.log 2>&1
```

(깃허브 Actions 로 돌릴 때는 짝수달에도 한 번 더 깨워야 한다. 60일 규칙 — `DEPLOY.md` 참고.)
