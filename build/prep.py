# -*- coding: utf-8 -*-
"""KCI 서지 엑셀 -> 그래프 JSON 정제 파이프라인"""
import pandas as pd, glob, re, json, unicodedata, os, collections

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLS = os.path.join(BASE, '한국복식학회', 'excel')

EXTRA = os.path.join(BASE, 'build', 'extra.json')   # fetch_new.py 가 채우는 최신호

def load():
    dfs = []
    for f in sorted(glob.glob(os.path.join(XLS, '*.xls'))):
        dfs.append(pd.read_excel(f, engine='xlrd'))
    if os.path.exists(EXTRA):
        rows = json.load(open(EXTRA, encoding='utf-8'))
        if rows:
            dfs.append(pd.DataFrame(rows))
            print(f'extra.json 최신호 {len(rows)}건 병합')
    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=['논문명', '발행연도', '시작 페이지'], keep='first')
    df = df.sort_values(['발행연도', '권', '호', '시작 페이지'], kind='stable')
    return df.reset_index(drop=True)

# 攀 뒤는 각주/교신저자/연구비 사사 -> 버림
SEP = '攀'
NOISE = re.compile(r'(e-?mail|@|지원을?\s*받|연구비|학위논문|石士|corresponding)', re.I)

def clean_kw_cell(cell):
    if not isinstance(cell, str):
        return []
    head = cell.split(SEP)[0]
    out = []
    for tok in re.split(r'[,;/]', head):
        t = unicodedata.normalize('NFKC', tok).strip().strip('.·-')
        if not t or NOISE.search(t):
            continue
        # "universal design(유니버설 디자인)" -> 한글 우선
        m = re.match(r'^(.*?)\(([^()]*[가-힣][^()]*)\)$', t)
        if m:
            t = m.group(2).strip()
        else:
            t = re.sub(r'\s*\([^()]*\)\s*$', '', t).strip()
        t = re.sub(r'\s+', ' ', t)
        if len(t) < 2 or len(t) > 30:
            continue
        if not re.search(r'[가-힣A-Za-z]', t):
            continue
        out.append(t)
    return out

def norm_kw(k):
    """표기 흔들림 통합용 키: 소문자, 공백/하이픈 제거"""
    return re.sub(r'[\s\-_·]', '', k.lower())

def clean_title(t):
    t = re.sub(r'<한문>', '□', str(t))
    return re.sub(r'\s+', ' ', t).strip()


# 원자료에 사람이 아닌 표시가 저자 자리에 들어온 것이 있다. 한자를 못 읽어
# '<한문>' 으로 적어 둔 칸이 그렇다. 사람 수를 셀 때 한 명으로 잡히면 안 된다.
NOT_A_NAME = {'nan', 'none', '', '<한문>', '□', '-', '.'}


def clean_author(a):
    a = re.sub(r'\s+', ' ', str(a)).strip()
    if a.lower() in NOT_A_NAME:
        return None
    # 낱자모가 음절 사이에 끼어 든 오타 — '김경ㅇ화' 처럼. 온전한 음절이 있을 때만 턴다.
    if re.search(r'[가-힣]', a):
        a = re.sub(r'[ㄱ-ㅎㅏ-ㅣ]', '', a).strip()
    return a or None

def main():
    df = load()
    papers, kw_raw = [], []
    for i, r in df.iterrows():
        kws = clean_kw_cell(r.get('저자키워드'))
        authors = [c for c in (clean_author(a) for a in str(r['저자명']).split(';')) if c]
        authors = list(dict.fromkeys(authors))      # 한 논문에 같은 이름이 두 번 적힌 칸이 있다
        papers.append({
            'id': f'p{i}',
            'title': clean_title(r['논문명']),
            'authors': authors,
            'affil': None if pd.isna(r.get('주저자 소속기관')) else str(r['주저자 소속기관']).strip(),
            'year': int(r['발행연도']),
            'vol': None if pd.isna(r.get('권')) else int(r['권']),
            'iss': None if pd.isna(r.get('호')) else int(r['호']),
            'sp': None if pd.isna(r.get('시작 페이지')) else int(r['시작 페이지']),
            'ep': None if pd.isna(r.get('끝 페이지')) else int(r['끝 페이지']),
            'cites': int(r['인용된 총 횟수']) if not pd.isna(r.get('인용된 총 횟수')) else 0,
            'kws': kws,
        })
        kw_raw += kws

    # 표기 통합: 정규화 키별로 가장 흔한 원표기를 대표로
    by_norm = collections.defaultdict(collections.Counter)
    for k in kw_raw:
        by_norm[norm_kw(k)][k] += 1
    canon = {n: c.most_common(1)[0][0] for n, c in by_norm.items()}
    for p in papers:
        seen, uniq = set(), []
        for k in p['kws']:
            c = canon[norm_kw(k)]
            if c not in seen:
                seen.add(c); uniq.append(c)
        p['kws'] = uniq

    kw_count = collections.Counter(k for p in papers for k in p['kws'])
    au_count = collections.Counter(a for p in papers for a in p['authors'])

    stats = {
        'papers': len(papers),
        'years': [min(p['year'] for p in papers), max(p['year'] for p in papers)],
        'kw_unique': len(kw_count),
        'au_unique': len(au_count),
        'papers_with_kw': sum(1 for p in papers if p['kws']),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print('\n-- 상위 키워드 40 --')
    for k, c in kw_count.most_common(40):
        print(f'  {c:4d}  {k}')
    print('\n-- 키워드 빈도 분포 --')
    dist = collections.Counter(kw_count.values())
    for th in (1, 2, 3, 5, 8, 12, 20):
        print(f'  {th}회 이상 등장 키워드: {sum(1 for v in kw_count.values() if v >= th)}')
    print('\n-- 상위 저자 15 --')
    for a, c in au_count.most_common(15):
        print(f'  {c:4d}  {a}')

    with open(os.path.join(BASE, 'build', 'papers.json'), 'w', encoding='utf-8') as f:
        json.dump({'papers': papers}, f, ensure_ascii=False)
    print('\nwrote build/papers.json')

main()
