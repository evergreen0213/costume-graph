# 배포와 자동 최신화

맥을 켜둘 필요가 없다. 깃허브가 매월 알아서 돌린다.

```
GitHub 저장소 ──(매월 1일 09:00 KST, Actions)──▶ build/update.sh
                                                       │
                                             costume-graph.html
                                                       │
                                                 GitHub Pages
                                                       │
       학회 홈페이지 커스텀 페이지 ◀── <iframe src="…"> 한 줄
```

## 처음 한 번만 하는 설정

### 1. 깃허브 로그인

터미널에서 (Claude Code 안이라면 앞에 `!` 를 붙여서):

```bash
gh auth login
```

### 2. 저장소 만들고 올리기

```bash
gh repo create costume-graph --public --source=. --remote=origin --push
```

> **공개(`--public`) / 비공개(`--private`)**
> Pages 를 무료로 쓰려면 공개 저장소여야 한다. 비공개로 두려면 GitHub Pro 이상이 필요하다.
> 공개로 두면 `한국복식학회/excel/*.xls` 안의 **초록 전문까지 함께 공개**된다.
> 어차피 KCI·DBpia 에서 열람되는 내용이고 학회가 저작권자이지만, 꺼려진다면
> `.gitignore` 에 `한국복식학회/ris/` 와 초록 열을 덜어낸 사본을 쓰는 쪽으로 바꾸면 된다.

### 3. Pages 켜기

저장소 → **Settings → Pages → Source** 를 **GitHub Actions** 로 바꾼다.
(기본값인 "Deploy from a branch" 로 두면 워크플로가 배포에 실패한다.)

### 4. 첫 배포 확인

**Actions** 탭 → `복식 서지 최신화` → **Run workflow** 로 손수 한 번 돌린다.
끝나면 주소가 나온다:

```
https://<계정명>.github.io/costume-graph/
```

### 5. 학회 홈페이지에 붙이기

관리자에서 커스텀 페이지를 하나 만들고 아래 한 줄을 넣는다.
지금 `/homepage/custom/search` 페이지가 DBpia 를 이런 식으로 넣고 있으므로 같은 방법이다.

```html
<IFRAME src="https://<계정명>.github.io/costume-graph/"
        width="100%" height="900" frameBorder="0"
        style="border:0;display:block"
        title="복식 연구 지도"></IFRAME>
```

이 뒤로는 손댈 일이 없다. 매월 1일에 새 호가 있으면 알아서 들어가고,
iframe 주소는 그대로라 홈페이지는 건드리지 않아도 된다.

## 평소에 벌어지는 일

| 시점 | 동작 |
|---|---|
| 매월 1일 09:00 KST | Actions 가 `update.sh` 실행 |
| 새 논문 없음 | "새 논문 없음" 찍고 그대로 종료. 커밋도 배포도 없음 |
| 새 논문 있음 | 수집 → 정제 → 그래프 → 군집 → 렌더 → 커밋 → Pages 배포 |

`build/**` 나 엑셀을 고쳐서 push 해도 다시 빌드된다.
급할 땐 Actions 탭에서 **Run workflow** 로 즉시 돌릴 수 있다.

## 왜 매월인가

『복식』은 격월간(연 6호)이다. 게다가 이 파이프라인이 보는 것은 KCI 가 아니라
**CrossRef 의 DOI 등록**이라, 호가 나온 뒤 등록까지 며칠~몇 주 걸릴 수 있다.
월 1회면 늦어도 한 달 안에 반영된다. 새 논문이 없으면 아무 일도 하지 않으므로
주 1회(`0 0 * * 1`)로 당겨도 부담은 없다.

## 손으로 돌리기

```bash
pip install -r requirements.txt
bash build/update.sh
```

자세한 내부 동작은 `build/README.md` 참고.
