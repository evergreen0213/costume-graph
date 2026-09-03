# -*- coding: utf-8 -*-
"""조각보 지도 데이터 — 보자기 안에 배치와 조각 모양까지 미리 계산해 굳힌다.

브라우저는 그리기만 한다. 매번 물리로 흔들면 지도가 아니라 실험이 된다.

한때 한반도 윤곽을 썼다가 걷어냈다. 실제 지명 위에 연구 갈래를 올리면 읽는 사람이
지역으로 읽는다 — "왜 내 분야가 강원도냐"는 반응이 나오고, 그건 타당한 반응이다.
조각보에는 위아래도 중심도 지명도 없다.
"""
import json, os, sys, collections, itertools, math
import numpy as np, networkx as nx
from networkx.algorithms.community import louvain_communities
from scipy.spatial import Voronoi
from scipy.ndimage import distance_transform_edt
from matplotlib.path import Path as MplPath
from shapely.geometry import Polygon as ShPoly, MultiPolygon

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, 'build'))
import hashlib, datetime
import designs

DESIGN = sys.argv[sys.argv.index('--design') + 1] if '--design' in sys.argv else 'bojagi'
KMIN, RES, SEED, MINC = 3, 0.8, 5, 20
papers = json.load(open(os.path.join(BASE, 'build', 'papers.json'), encoding='utf-8'))['papers']

# ── 지도에 오를 키워드 ────────────────────────────────────────────────
kc = collections.Counter(k for p in papers for k in p['kws'])
keep = {k for k, c in kc.items() if c >= KMIN}
co = collections.Counter()
for p in papers:
    for a, b in itertools.combinations(sorted({k for k in p['kws'] if k in keep}), 2):
        co[(a, b)] += 1
# set 을 그대로 넣으면 삽입 순서가 프로세스마다 달라져 군집이 흔들린다. 경계에서 정렬한다.
g = nx.Graph(); g.add_nodes_from(sorted(keep))
for (a, b), c in sorted(co.items()):
    g.add_edge(a, b, weight=c)
giant = max(nx.connected_components(g), key=lambda c: (len(c), min(c)))
gg = g.subgraph(sorted(giant)).copy()

comms = louvain_communities(gg, weight='weight', resolution=RES, seed=SEED)
comms = [sorted(c) for c in comms]
comms.sort(key=lambda c: (-len(c), c[0]))
big = [c for c in comms if len(c) >= MINC]
rest = sorted(k for c in comms if len(c) < MINC for k in c)
comm_of = {k: i for i, c in enumerate(big) for k in c}
for k in rest:                                     # 작은 군집은 가장 많이 이어진 갈래로 흡수
    tally = collections.Counter()
    for nb in sorted(gg[k]):
        if nb in comm_of:
            tally[comm_of[nb]] += gg[k][nb]['weight']
    comm_of[k] = tally.most_common(1)[0][0] if tally else 0
NG = len(big)

# 대표 키워드 -> 손질한 이름. 검수에서 실제 구성과 어긋난 이름을 바로잡았다.
CURATED = {
    '무대의상': '패션 이미지와 표현',      # 무대의상·일러스트·스트리트·남성복이 함께 있다
    '조선시대': '조선시대 복식사',
    '영화의상': '복식의 상징과 미의식',    # 영화의상만이 아니라 상징·조형·인체가 함께
    '문화상품': '문화상품과 디자인 개발',
    '메이크업': '외모 관리와 착장 행동',
    '구매의도': '브랜드와 구매 심리',
    '패션디자인': '현대 패션 디자인',
    '한복': '한복과 전통의 재현',
    '복식': '근대 복식과 색채',
    '지속가능성': '지속가능 패션과 새 세대',
    '패션쇼': '한국 근현대 패션사',
    '전통복식': '전통 복식의 미의식',
    '색채': '근대 복식과 문양',
    '패션': '현대 패션 디자인',
}
GLYPHS = ['저고리', '흉배', '원삼', '노리개', '버선', '갓', '조각보', '부채', '삼태극', '연꽃']

names, tops, used = [], [], set()
for gi in range(NG):
    ks = sorted([k for k, c in comm_of.items() if c == gi], key=lambda k: (-kc[k], k))
    tops.append(ks[:6])
    cand = CURATED.get(ks[0])
    if cand is None or cand in used:
        cand = ' · '.join(ks[:2]); i = 2
        while cand in used and i < len(ks):
            cand = f'{ks[0]} · {ks[i]}'; i += 1
    used.add(cand); names.append(cand)

kws = sorted(giant, key=lambda k: (-kc[k], k))
kidx = {k: i for i, k in enumerate(kws)}
n = len(kws)
kp = [[] for _ in kws]; yrs = [[] for _ in kws]
for pi, p in enumerate(papers):
    for k in p['kws']:
        j = kidx.get(k)
        if j is not None:
            kp[j].append(pi); yrs[j].append(p['year'])
for y in yrs: y.sort()
CM = np.array([comm_of[k] for k in kws])
edges = [(kidx[a], kidx[b], c) for (a, b), c in sorted(co.items()) if a in kidx and b in kidx]

# ── 틀 ────────────────────────────────────────────────────────────────
DS = designs.build(DESIGN, NG)
LAND = [tuple(p) for p in DS['frame']]
REGIONS = [ShPoly([tuple(q) for q in r]) for r in DS['regions']] if DS['regions'] else None
land_poly = ShPoly(LAND)
LX0, LY0, LX1, LY1 = land_poly.bounds
LX0, LY0, LX1, LY1 = land_poly.bounds

# ── 안쪽으로 밀어 넣는 힘을 위한 거리장 ───────────────────────────────
GRID = 6.0

def make_sdf(poly):
    """다각형 안쪽이 음수인 거리장과 그 기울기. 밖이면 양수."""
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    gx = np.arange(min(xs) - 40, max(xs) + 40, GRID)
    gy = np.arange(min(ys) - 40, max(ys) + 40, GRID)
    GX, GY = np.meshgrid(gx, gy)
    ins = MplPath(poly).contains_points(np.column_stack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
    sdf = distance_transform_edt(~ins) * GRID - distance_transform_edt(ins) * GRID
    sy, sx = np.gradient(sdf, GRID)
    return {'gx': gx, 'gy': gy, 'sdf': sdf, 'sx': sx, 'sy': sy}

def sdf_query(F, P):
    ix = np.clip(((P[:, 0] - F['gx'][0]) / GRID).astype(int), 0, len(F['gx']) - 1)
    iy = np.clip(((P[:, 1] - F['gy'][0]) / GRID).astype(int), 0, len(F['gy']) - 1)
    return F['sdf'][iy, ix], F['sx'][iy, ix], F['sy'][iy, ix]

FRAME_SDF = make_sdf(LAND)
REGION_SDF = [make_sdf([tuple(q) for q in r]) for r in DS['regions']] if DS['regions'] else None

def sdf_at(P, comm=None):
    """구역이 정해진 디자인이면 제 구역 기준으로, 아니면 틀 전체 기준으로 잰다."""
    if REGION_SDF is None or comm is None:
        return sdf_query(FRAME_SDF, P)
    s = np.zeros(len(P)); sx = np.zeros(len(P)); sy = np.zeros(len(P))
    for gi, F in enumerate(REGION_SDF):
        m = comm == gi
        if not m.any(): continue
        a, b, c = sdf_query(F, P[m])
        s[m] = a; sx[m] = b; sy[m] = c
    return s, sx, sy

# ── 갈래 자리 ─────────────────────────────────────────────────────────
if REGIONS is not None:
    # 구역이 미리 정해진 디자인(책가도·색동). 자리는 구역 한가운데.
    A = np.array([[r.representative_point().x, r.representative_point().y] for r in REGIONS])
else:
    # 유기적 디자인(조각보·흉배). 연관성으로 배열하고 틀 안에 고르게 편다.
    meta = nx.Graph(); meta.add_nodes_from(range(NG))
    mw = collections.Counter()
    for a, b, c in edges:
        if CM[a] != CM[b]: mw[(min(CM[a], CM[b]), max(CM[a], CM[b]))] += c
    for (a, b), c in sorted(mw.items()): meta.add_edge(a, b, weight=c)
    mpos = nx.spring_layout(meta, weight='weight', seed=11, iterations=900, k=2.6)
    A = np.array([mpos[i] for i in range(NG)], dtype=float)
    A -= A.mean(0)
    A[:, 0] *= (LX1 - LX0) * 0.34 / (np.abs(A[:, 0]).max() or 1)
    A[:, 1] *= (LY1 - LY0) * 0.40 / (np.abs(A[:, 1]).max() or 1)
    A[:, 0] += (LX0 + LX1) / 2 - A[:, 0].mean()
    A[:, 1] += (LY0 + LY1) / 2 - A[:, 1].mean()

    # 자리를 틀에 고르게 편다 (Lloyd 완화). 안 하면 한쪽에 몰려 절반이 빈다.
    rs = np.random.default_rng(9)
    samp = np.column_stack([rs.uniform(LX0, LX1, 24000), rs.uniform(LY0, LY1, 24000)])
    samp = samp[MplPath(LAND).contains_points(samp)]
    size = np.array([(CM == i).sum() for i in range(NG)], dtype=float)
    pull = np.sqrt(size / size.mean())
    for _ in range(60):
        dist = np.linalg.norm(samp[:, None, :] - A[None, :, :], axis=2) / pull[None, :]
        own = dist.argmin(1)
        for gi in range(NG):
            m = own == gi
            if m.sum() > 8:
                A[gi] = 0.75 * samp[m].mean(0) + 0.25 * A[gi]
        ls_, lx_, ly_ = sdf_query(FRAME_SDF, A)
        bad = ls_ > -110
        if bad.any():
            gn = np.hypot(lx_, ly_); gn[gn == 0] = 1
            A[bad, 0] -= (lx_[bad] / gn[bad]) * (ls_[bad] + 110) * 0.6
            A[bad, 1] -= (ly_[bad] / gn[bad]) * (ls_[bad] + 110) * 0.6

# ── 배치 ──────────────────────────────────────────────────────────────
rng = np.random.default_rng(4)
P = A[CM] + rng.normal(0, 30, (n, 2))
V = np.zeros((n, 2))
ei = np.array([e[0] for e in edges]); ej = np.array([e[1] for e in edges])
ew = np.minimum(1 + np.log(np.array([e[2] for e in edges], dtype=float)), 3.0)
deg = np.bincount(np.concatenate([ei, ej]), minlength=n).astype(float)
wi = 1 / (1 + deg)

REPEL, LINK_D, LINK_K, CLUST, DECAY = 300.0, 40.0, 0.55, 0.20, 0.86
if REGIONS is not None:
    # 구역이 정해진 디자인. 점이 구석에 뭉치지 않고 칸을 채우도록,
    # 밀어내는 힘을 구역 넓이에 맞춰 잡고 당기는 힘은 약하게 둔다.
    area = np.mean([r.area for r in REGIONS])
    per = max(1.0, n / NG)
    REPEL = float(np.clip(area / per * 0.012, 90.0, 420.0))
    LINK_D, LINK_K, CLUST = 30.0, 0.45, 0.06
alpha = 1.0
for step in range(1500):
    d = P[:, None, :] - P[None, :, :]
    d2 = (d ** 2).sum(-1); np.fill_diagonal(d2, 1e9); np.maximum(d2, 4.0, out=d2)
    V += (d * (REPEL * alpha / d2)[:, :, None]).sum(1)

    dv = P[ej] - P[ei]; L = np.hypot(dv[:, 0], dv[:, 1]); L[L == 0] = 1
    f = ((L - LINK_D) / L * alpha * LINK_K * ew)[:, None] * dv
    tot = (wi[ei] + wi[ej])[:, None]
    np.add.at(V, ei, f * (wi[ej][:, None] / tot) * 2)
    np.add.at(V, ej, -f * (wi[ei][:, None] / tot) * 2)

    V += (A[CM] - P) * CLUST * alpha
    s, sx, sy = sdf_at(P, CM)                      # 제 구역 밖으로 나가지 않게 붙잡는다
    near = s > -90
    if near.any():
        gn = np.hypot(sx, sy); gn[gn == 0] = 1
        push = np.clip(s + 90, 0, None) * 0.22
        V[near, 0] -= (sx[near] / gn[near]) * push[near]
        V[near, 1] -= (sy[near] / gn[near]) * push[near]
    V *= DECAY
    sp = np.hypot(V[:, 0], V[:, 1]); m = sp > 24
    V[m] *= (24 / sp[m])[:, None]
    P += V
    alpha *= 0.9976

# 그래도 밖에 있는 점은 확실히 안으로 넣는다. 한 번 미는 것으로는 모자라
# 밀린 자리가 또 밖일 수 있어, 남지 않을 때까지 되풀이한다.
MARGIN = 30.0 if REGIONS is None else 14.0
for _ in range(60):
    s_, sx_, sy_ = sdf_at(P, CM)
    out_ = s_ > -MARGIN
    if not out_.any():
        break
    gn = np.hypot(sx_, sy_); gn[gn == 0] = 1
    P[out_, 0] -= (sx_[out_] / gn[out_]) * (s_[out_] + MARGIN) * 0.9
    P[out_, 1] -= (sy_[out_] / gn[out_]) * (s_[out_] + MARGIN) * 0.9

# ── 조각보: 보로노이 칸을 한반도 모양으로 잘라낸다 ────────────────────
far = max(LX1 - LX0, LY1 - LY0) * 6
guard = np.array([[far, far], [-far, far], [far, -far], [-far, -far],
                  [0, far * 1.5], [0, -far * 1.5], [far * 1.5, 0], [-far * 1.5, 0]])
vor = Voronoi(np.vstack([P, guard]))
def poly_of(i):
    reg = vor.regions[vor.point_region[i]]
    if not reg or -1 in reg: return None
    return ShPoly([tuple(vor.vertices[v]) for v in reg]).buffer(0)

cells = []
for i in range(n):
    q = poly_of(i)
    if q is None or q.is_empty:
        cells.append([]); continue
    q = q.intersection(REGIONS[CM[i]] if REGIONS is not None else land_poly)
    if q.is_empty: cells.append([]); continue
    if isinstance(q, MultiPolygon): q = max(q.geoms, key=lambda z: z.area)
    cells.append([[round(x, 1), round(y, 1)] for x, y in q.exterior.coords[:-1]])

seams = []
for (p_, q_), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices) if REGIONS is None else []:
    if p_ >= n or q_ >= n or CM[p_] == CM[q_]: continue
    if v1 == -1 or v2 == -1: continue
    from shapely.geometry import LineString
    seg = LineString([tuple(vor.vertices[v1]), tuple(vor.vertices[v2])]).intersection(land_poly)
    if seg.is_empty or seg.geom_type != 'LineString': continue
    (ax_, ay_), (bx_, by_) = seg.coords[0], seg.coords[-1]
    seams.append([round(ax_, 1), round(ay_, 1), round(bx_, 1), round(by_, 1)])

# 이름패는 갈래 한가운데에서 시작해, 겹치면 밀어낸다
LP = np.array([[P[CM == gi, 0].mean(), P[CM == gi, 1].mean()] for gi in range(NG)])
LW = np.array([len(names[gi]) * 19 + 42 for gi in range(NG)], dtype=float)
LH = 58.0
for _ in range(700):
    for a in range(NG):
        for b in range(a + 1, NG):
            dx = LP[b, 0] - LP[a, 0]; dy = LP[b, 1] - LP[a, 1]
            ox = (LW[a] + LW[b]) / 2 - abs(dx); oy = LH * 1.3 - abs(dy)
            if ox > 0 and oy > 0:
                if ox / (LW[a] + LW[b]) < oy / (LH * 2.6):
                    sh = ox / 2 * (1 if dx >= 0 else -1); LP[a, 0] -= sh; LP[b, 0] += sh
                else:
                    sh = oy / 2 * (1 if dy >= 0 else -1); LP[a, 1] -= sh; LP[b, 1] += sh
    ls, lsx, lsy = sdf_at(LP, np.arange(NG))       # 이름패가 제 구역을 벗어나지 않게
    bad = ls > -115
    if bad.any():
        gn2 = np.hypot(lsx, lsy); gn2[gn2 == 0] = 1
        LP[bad, 0] -= (lsx[bad] / gn2[bad]) * (ls[bad] + 115) * 0.6
        LP[bad, 1] -= (lsy[bad] / gn2[bad]) * (ls[bad] + 115) * 0.6

# ── 상세층 ────────────────────────────────────────────────────────────
PPq = [[p['title'], p['year'], p['cites'], p['vol'] or 0, p['iss'] or 0,
        p['sp'] or 0, p['ep'] or 0, p['affil'] or ''] for p in papers]
au = collections.defaultdict(list)
for pi, p in enumerate(papers):
    for a in p['authors']: au[a].append(pi)
AU = [[a, v] for a, v in sorted(au.items(), key=lambda x: (-len(x[1]), x[0]))]

out = {
    'kw': [[kws[i], len(kp[i]), yrs[i][len(yrs[i]) // 2], int(CM[i]),
            round(float(P[i, 0]), 1), round(float(P[i, 1]), 1)] for i in range(n)],
    'kl': [[a, b, c] for a, b, c in edges],
    'cells': cells, 'seams': seams,
    'land': [[round(x, 1), round(y, 1)] for x, y in LAND],
    'decor': DS['decor'], 'design': DESIGN, 'designLabel': DS['label'],
    'fields': [{'name': names[gi], 'top': tops[gi],
                'at': [round(float(LP[gi, 0]), 1), round(float(LP[gi, 1]), 1)],
                'gat': [round(float(A[gi, 0]), 1), round(float(A[gi, 1]), 1)],
                'glyph': GLYPHS[gi % len(GLYPHS)],
                'kws': int((CM == gi).sum()),
                'papers': len({pi for i in range(n) if CM[i] == gi for pi in kp[i]})}
               for gi in range(NG)],
    'glyphs': json.load(open(os.path.join(BASE, 'build', 'glyphs.json'), encoding='utf-8')),
    'kp': kp, 'papers': PPq, 'pa': [p['authors'] for p in papers],
    'pk': [[kidx[k] for k in p['kws'] if k in kidx] for p in papers], 'authors': AU,
}
# 판 번호 — 내용을 해시한다. 날짜로 찍으면 아무것도 안 바뀐 달에도 새 판이 되어
# 보는 사람마다 476 KB 를 새로 받는다. 지도가 실제로 달라질 때만 값이 바뀌어야 한다.
blob = json.dumps(out, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
out['build'] = hashlib.sha256(blob.encode('utf-8')).hexdigest()[:16]
out['builtAt'] = datetime.date.today().isoformat()

path = os.path.join(BASE, 'build', f'view-{DESIGN}.json')
json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

outside = int((sdf_at(P, CM)[0] > 0).sum())
print(f"[{DESIGN}] {DS['label']} — 키워드 {n} · 이음선 {len(edges)} · 조각 {sum(1 for c in cells if c)} · 바느질선 {len(seams)} · 장식 {len(DS['decor'])}")
print(f'틀 밖으로 나간 점 {outside}개 · 빈 조각 {sum(1 for c in cells if not c)}개')
print(f'연구 갈래 {NG}개')
for gi, f in enumerate(out['fields']):
    print(f"  [{gi}] {f['name']:<20} {f['glyph']:<4} 키워드 {f['kws']:3d}  논문 {f['papers']:4d}")
print(f'논문 {len(PPq)}편 · 연구자 {len(AU)}명 · {os.path.getsize(path)/1024:.0f} KB')
