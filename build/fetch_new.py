# -*- coding: utf-8 -*-
"""CrossRef + DBpia 로 최신 『복식』 논문을 받아 build/extra.json 에 누적한다.

인증키 없이 동작한다.
  1) CrossRef(ISSN 1229-6880)에서 DOI/권/호/페이지/발행일을 받고
  2) DOI를 따라가면 도착하는 DBpia 상세 페이지의 citation_* 메타에서
     한글 논문명 / 한글 저자명 / 저자키워드를 긁는다.
extra.json 은 누적 캐시라 다시 돌려도 이미 받은 논문은 건드리지 않는다.
"""
import json, os, re, sys, time, html, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRA = os.path.join(BASE, 'build', 'extra.json')
PAPERS = os.path.join(BASE, 'build', 'papers.json')
ISSN = '1229-6880'
MAILTO = os.environ.get('CROSSREF_MAILTO', 'kscostume@ksc.or.kr')
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'
SLEEP = float(os.environ.get('FETCH_SLEEP', '1.5'))


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'ko,en;q=0.8'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or 'utf-8', 'replace')


# ── 1. CrossRef: 저널 전체 목록 ────────────────────────────────────────────
def crossref_works():
    out, cursor = [], '*'
    while True:
        q = urllib.parse.urlencode({
            'rows': 500, 'cursor': cursor, 'mailto': MAILTO,
            'select': 'DOI,volume,issue,page,published,title,original-title',
        })
        m = json.loads(get(f'https://api.crossref.org/journals/{ISSN}/works?{q}'))['message']
        items = m.get('items', [])
        if not items:
            break
        out += items
        cursor = m.get('next-cursor')
        if not cursor:
            break
    return out


# ── 2. DBpia 상세 메타 ────────────────────────────────────────────────────
META = re.compile(r'<meta\s+name="(citation_[a-z_]+)"\s+content="(.*?)"\s*/?>', re.I | re.S)


def dbpia_meta(doi):
    h = get('https://doi.org/' + doi)
    d = {}
    for k, v in META.findall(h):
        v = html.unescape(v).strip()
        d.setdefault(k, []).append(v)
    return d


def clean_title(t):
    t = re.sub(r'\s+', ' ', t).strip()
    return re.sub(r'\s*[-–]\s*$', '', t).strip()


def to_int(v):
    try:
        return int(re.sub(r'\D', '', str(v)))
    except (TypeError, ValueError):
        return None


KW_KO = re.compile(r'^(.*?)\s*\(([^()]*[가-힣][^()]*)\)$')


def norm_keywords(vals):
    """DBpia 의 'english (한글)' 목록 -> 엑셀 저자키워드와 같은 한글 콤마 목록.

    낱말 안의 구분자(, ; /)는 prep.py 의 분리 규칙과 충돌하므로 미리 없앤다.
    예: 'cosmetic/plastic surgery intention (미용/성형 의도)' -> '미용·성형 의도'
    """
    out = []
    for raw in vals:
        for tok in raw.split(';'):
            t = tok.strip()
            if not t:
                continue
            m = KW_KO.match(t)
            if m:
                t = m.group(2).strip()
            t = re.sub(r'\s*/\s*', '·', t)
            t = re.sub(r'[,;]', ' ', t)
            t = re.sub(r'\s+', ' ', t).strip()
            if t:
                out.append(t)
    return out


def build_record(it, meta):
    """엑셀 컬럼과 같은 모양으로 만든다 (prep.py 가 그대로 이어붙일 수 있게)."""
    title = clean_title((meta.get('citation_title') or it.get('original-title') or it.get('title') or [''])[0])
    authors = [a for a in meta.get('citation_author', []) if a.strip()]
    kw_raw = meta.get('citation_keywords', [])
    page = it.get('page') or ''
    sp, ep = (page.split('-') + [''])[:2]
    year = (it.get('published', {}).get('date-parts') or [[None]])[0][0]
    return {
        '유형': 'J',
        '저자명': ';'.join(authors),
        '주저자 소속기관': None,               # DBpia 메타에는 소속이 없다
        '논문명': title,
        '학술지명': '복식',
        '언어': '한국어',
        '저자키워드': ', '.join(norm_keywords(kw_raw)),
        '_keywords_raw': '; '.join(kw_raw),   # 원본 보존 (정제 규칙이 바뀌어도 재수집 불필요)
        '인용된 총 횟수': 0,
        '발행기관명': '한국복식학회',
        '발행연도': to_int(meta.get('citation_publication_date', [year])[0][:4]) or year,
        '권': to_int(meta.get('citation_volume', [it.get('volume')])[0]) or to_int(it.get('volume')),
        '호': to_int(meta.get('citation_issue', [it.get('issue')])[0]) or to_int(it.get('issue')),
        '시작 페이지': to_int(meta.get('citation_firstpage', [sp])[0]) or to_int(sp),
        '끝 페이지': to_int(meta.get('citation_lastpage', [ep])[0]) or to_int(ep),
        'DOI': it['DOI'],
    }


# ── 3. 기존 데이터와 대조 ─────────────────────────────────────────────────
def norm_title(t):
    return re.sub(r'[^가-힣a-z0-9]', '', str(t).lower())


def known_keys():
    """엑셀에서 이미 만들어진 papers.json 기준 중복 판별 키."""
    if not os.path.exists(PAPERS):
        return set(), set()
    ps = json.load(open(PAPERS, encoding='utf-8'))['papers']
    return ({(p['vol'], p['iss'], p['sp']) for p in ps},
            {norm_title(p['title']) for p in ps})


def main():
    extra = []
    if os.path.exists(EXTRA):
        extra = json.load(open(EXTRA, encoding='utf-8'))
    have_doi = {e['DOI'] for e in extra}
    vis, tis = known_keys()

    print('CrossRef 조회 중…', flush=True)
    works = crossref_works()
    print(f'  CrossRef 레코드 {len(works)}건')

    todo = []
    for it in works:
        doi = it.get('DOI')
        if not doi or doi in have_doi:
            continue
        page = it.get('page') or ''
        key = (to_int(it.get('volume')), to_int(it.get('issue')), to_int(page.split('-')[0]))
        t = norm_title((it.get('original-title') or it.get('title') or [''])[0])
        if key in vis or (t and t in tis):
            continue
        todo.append(it)

    if not todo:
        print('새 논문 없음. 이미 최신입니다.')
        return 0

    todo.sort(key=lambda x: (to_int(x.get('volume')) or 0, to_int(x.get('issue')) or 0,
                             to_int((x.get('page') or '0').split('-')[0]) or 0))
    print(f'새 논문 후보 {len(todo)}건 — DBpia 상세 수집')

    ok = fail = 0
    for i, it in enumerate(todo, 1):
        doi = it['DOI']
        try:
            meta = dbpia_meta(doi)
        except Exception as e:                                  # noqa: BLE001
            print(f'  [{i}/{len(todo)}] {doi}  실패: {e}')
            fail += 1
            time.sleep(SLEEP)
            continue
        rec = build_record(it, meta)
        if not rec['논문명'] or not rec['저자명']:
            print(f'  [{i}/{len(todo)}] {doi}  메타 부족 — 건너뜀')
            fail += 1
            time.sleep(SLEEP)
            continue
        extra.append(rec)
        ok += 1
        print(f"  [{i}/{len(todo)}] {rec['권']}({rec['호']}) {rec['시작 페이지']}p  {rec['논문명'][:38]}")
        time.sleep(SLEEP)

    extra.sort(key=lambda e: (e['발행연도'] or 0, e['권'] or 0, e['호'] or 0, e['시작 페이지'] or 0))
    json.dump(extra, open(EXTRA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n추가 {ok}건 / 실패 {fail}건  →  build/extra.json (누적 {len(extra)}건)')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
