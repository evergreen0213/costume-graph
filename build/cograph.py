# -*- coding: utf-8 -*-
"""키워드 동시출현 지도 — 기본 화면이 될 성긴 그래프"""
import json, os, collections, itertools, networkx as nx
from networkx.algorithms.community import louvain_communities

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G_ = json.load(open(os.path.join(BASE, 'build', 'graph.json'), encoding='utf-8'))
N, NP = G_['nodes'], G_['nPapers']
papers = json.load(open(os.path.join(BASE, 'build', 'papers.json'), encoding='utf-8'))['papers']

kw_idx = {N[i][1]: i for i in range(NP, len(N)) if N[i][0] == 1}

co = collections.Counter()
for p in papers:
    ks = sorted({k for k in p['kws'] if k in kw_idx})
    for a, b in itertools.combinations(ks, 2):
        co[(a, b)] += 1

klinks = [[kw_idx[a], kw_idx[b], c] for (a, b), c in co.items()]

# 키워드만의 군집 — 배치가 아니라 '갈래 이름'을 위해 쓴다
g = nx.Graph()
g.add_nodes_from(kw_idx.values())
for a, b, c in klinks:
    g.add_edge(a, b, weight=c)
comms = louvain_communities(g, weight='weight', resolution=1.0, seed=5)
comms.sort(key=len, reverse=True)
comms = [c for c in comms if len(c) >= 25]

kcomm = {}
names = []
for ci, c in enumerate(comms):
    for v in c:
        kcomm[v] = ci
    top = sorted(c, key=lambda v: -N[v][3])[:2]
    names.append(' · '.join(N[v][1] for v in top))

# 키워드별 연구 시기 (그 키워드가 쓰인 논문 발행연도의 중앙값)
years = collections.defaultdict(list)
for i, p in enumerate(papers):
    for k in p['kws']:
        if k in kw_idx:
            years[kw_idx[k]].append(p['year'])
kyear = {}
for v, ys in years.items():
    ys.sort()
    kyear[v] = ys[len(ys) // 2]

kmeta = []
for i in range(NP, len(N)):
    if N[i][0] != 1:
        continue
    kmeta.append([i, kcomm.get(i, -1), kyear.get(i, 0)])

print(f'키워드 {len(kw_idx)}개, 동시출현 간선 {len(klinks)}개')
print(f'군집 {len(comms)}개 (25개 이상):')
for ci, nm in enumerate(names):
    print(f'  [{ci}] {nm}  — 키워드 {len(comms[ci])}개')
print(f'군집 미배정 키워드 {sum(1 for _,c,_ in kmeta if c<0)}개')
print(f'연도 범위 {min(kyear.values())}–{max(kyear.values())}')

G_['klinks'] = klinks
G_['kmeta'] = kmeta
G_['kfields'] = names
json.dump(G_, open(os.path.join(BASE, 'build', 'graph.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print('graph.json 갱신')
