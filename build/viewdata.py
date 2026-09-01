# -*- coding: utf-8 -*-
"""화면이 실제로 쓰는 모양으로 데이터를 만든다 — 키워드 지도 + 논문 상세층"""
import json, os, collections, itertools, networkx as nx
from networkx.algorithms.community import louvain_communities

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
papers = json.load(open(os.path.join(BASE, 'build', 'papers.json'), encoding='utf-8'))['papers']

KMIN = 2
kc = collections.Counter(k for p in papers for k in p['kws'])
keep = {k for k, c in kc.items() if c >= KMIN}

co = collections.Counter()
for p in papers:
    for a, b in itertools.combinations(sorted({k for k in p['kws'] if k in keep}), 2):
        co[(a, b)] += 1

g = nx.Graph()
g.add_nodes_from(keep)
for (a, b), c in co.items():
    g.add_edge(a, b, weight=c)
giant = max(nx.connected_components(g), key=len)      # 떠도는 키워드는 지도에서 뺀다
gg = g.subgraph(giant).copy()

comms = louvain_communities(gg, weight='weight', resolution=1.0, seed=5)
comms.sort(key=len, reverse=True)
comms = [c for c in comms if len(c) >= 25]
comm_of = {v: i for i, c in enumerate(comms) for v in c}

names = sorted(giant, key=lambda k: (-kc[k], k))
kidx = {k: i for i, k in enumerate(names)}

kp = [[] for _ in names]
years = [[] for _ in names]
for pi, p in enumerate(papers):
    for k in p['kws']:
        j = kidx.get(k)
        if j is not None:
            kp[j].append(pi); years[j].append(p['year'])
for y in years:
    y.sort()

kw = [[k, len(kp[i]), years[i][len(years[i]) // 2], comm_of.get(k, -1)] for i, k in enumerate(names)]
kl = [[kidx[a], kidx[b], c] for (a, b), c in co.items() if a in kidx and b in kidx]

fields = []
for c in comms:
    top = sorted(c, key=lambda k: -kc[k])[:2]
    fields.append(' · '.join(top))

# ── 갈래 자리: 갈래끼리의 연결로 배치하고 크기만큼 밀어낸다 ──
NG = len(comms)
meta = nx.Graph(); meta.add_nodes_from(range(NG))
mw = collections.Counter()
for a, b, c in kl:
    ca, cb = kw[a][3], kw[b][3]
    if ca >= 0 and cb >= 0 and ca != cb:
        mw[(min(ca, cb), max(ca, cb))] += c
for (a, b), c in mw.items():
    meta.add_edge(a, b, weight=c)
pos = nx.spring_layout(meta, weight='weight', seed=11, iterations=800, k=2.4)
xs = [pos[i][0] for i in range(NG)]; ys = [pos[i][1] for i in range(NG)]
cx0, cy0 = sum(xs) / NG, sum(ys) / NG
span = max(max(abs(v - cx0) for v in xs), max(abs(v - cy0) for v in ys)) or 1
A = [[(pos[i][0] - cx0) / span * 900, (pos[i][1] - cy0) / span * 900] for i in range(NG)]
rad = [26 * (len(comms[i]) ** 0.5) for i in range(NG)]
for _ in range(400):
    for a in range(NG):
        for b in range(a + 1, NG):
            dx = A[b][0] - A[a][0]; dy = A[b][1] - A[a][1]
            d = (dx * dx + dy * dy) ** 0.5 or 1
            need = (rad[a] + rad[b]) * 1.05
            if d < need:
                q = (need - d) / 2 / d
                A[a][0] -= dx * q; A[a][1] -= dy * q
                A[b][0] += dx * q; A[b][1] += dy * q

# ── 논문 상세층 ──
P = [[p['title'], p['year'], p['cites'], p['vol'] or 0, p['iss'] or 0,
      p['sp'] or 0, p['ep'] or 0, p['affil'] or ''] for p in papers]
PA = [p['authors'] for p in papers]
PK = [[kidx[k] for k in p['kws'] if k in kidx] for p in papers]

au = collections.defaultdict(list)
for pi, p in enumerate(papers):
    for a in p['authors']:
        au[a].append(pi)
AU = [[a, v] for a, v in sorted(au.items(), key=lambda x: -len(x[1]))]

out = {'kw': kw, 'kl': kl, 'fields': fields, 'anchors': [[round(v, 1) for v in p] for p in A],
       'kp': kp, 'papers': P, 'pa': PA, 'pk': PK, 'authors': AU}
path = os.path.join(BASE, 'build', 'view.json')
json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print(f'키워드 {len(kw)}개 (지도에 오른 것), 동시출현 간선 {len(kl)}개')
print(f'연구 갈래 {NG}개')
for i, f in enumerate(fields):
    print(f'  [{i:2d}] {f:<30} 키워드 {len(comms[i]):3d}개')
print(f'갈래 미배정 키워드 {sum(1 for k in kw if k[3] < 0)}개')
print(f'논문 {len(P)}편, 연구자 {len(AU)}명')
print(f'{path}  {os.path.getsize(path)/1024:.0f} KB')
