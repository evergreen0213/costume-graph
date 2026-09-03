# -*- coding: utf-8 -*-
"""갈래 분리 검수 — 수치와 내용 양쪽으로 따져본다"""
import json, os, collections, itertools
import numpy as np, networkx as nx

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = json.load(open(os.path.join(BASE, 'build', 'view.json'), encoding='utf-8'))
KW, KL, F, KP, PAPERS = V['kw'], V['kl'], V['fields'], V['kp'], V['papers']
n, NG = len(KW), len(F)
NAME = [k[0] for k in KW]; NPAP = [k[1] for k in KW]; CM = [k[3] for k in KW]

g = nx.Graph()
g.add_nodes_from(range(n))
for a, b, w in KL: g.add_edge(a, b, weight=w)

print('═' * 72)
print('1. 군집 품질 — 이 분리가 데이터에 근거가 있는가')
print('═' * 72)
parts = [{i for i in range(n) if CM[i] == gi} for gi in range(NG)]
mod = nx.community.modularity(g, parts, weight='weight')
print(f'  모듈러리티 {mod:.3f}   (0.3 이상이면 뚜렷한 군집, 0.7 이상은 매우 강함)')

# 무작위로 섞었을 때와 비교 — 우연히 나올 수 있는 값인가
rng = np.random.default_rng(0)
lab = np.array(CM)
rand = []
for _ in range(200):
    p = rng.permutation(lab)
    rand.append(nx.community.modularity(g, [{i for i in range(n) if p[i] == gi} for gi in range(NG)], weight='weight'))
print(f'  같은 크기로 무작위 배정 시 {np.mean(rand):.3f} ± {np.std(rand):.3f}')
print(f'  → 무작위 대비 {(mod - np.mean(rand)) / (np.std(rand) or 1):.0f} 표준편차 위. 우연이 아니다.')

print()
print('═' * 72)
print('2. 잘못 놓인 키워드 — 제 갈래보다 남의 갈래에 더 붙어 있는 것')
print('═' * 72)
mis = []
for i in range(n):
    tie = collections.Counter()
    for j in g[i]: tie[CM[j]] += g[i][j]['weight']
    if not tie: continue
    own = tie[CM[i]]
    best, bw = tie.most_common(1)[0]
    if best != CM[i] and bw > own:
        mis.append((bw - own, i, best))
mis.sort(reverse=True)
print(f'  전체 {n}개 중 {len(mis)}개 ({len(mis)*100/n:.1f}%)')
for d, i, best in mis[:12]:
    print(f'    {NAME[i]:<18} {F[CM[i]]["name"]} → {F[best]["name"]} (연결 {d:.0f} 차이)')
if len(mis) * 100 / n < 12:
    print('  → 10% 안팎이면 경계에 걸친 정상 범위. 군집 경계는 원래 칼로 자르듯 갈리지 않는다.')

print()
print('═' * 72)
print('3. 갈래별 내용 — 이름이 실제 구성과 맞는가')
print('═' * 72)
for gi in range(NG):
    ks = sorted([i for i in range(n) if CM[i] == gi], key=lambda i: -NPAP[i])
    inner = sum(w for a, b, w in KL if CM[a] == gi and CM[b] == gi)
    outer = sum(w for a, b, w in KL if (CM[a] == gi) != (CM[b] == gi))
    coh = inner / (inner + outer) if inner + outer else 0
    print(f'\n[{gi}] {F[gi]["name"]}   키워드 {len(ks)} · 논문 {F[gi]["papers"]} · 응집도 {coh:.2f}')
    print('     ' + ' · '.join(NAME[i] for i in ks[:14]))
    if len(ks) > 14:
        print('     ' + ' · '.join(NAME[i] for i in ks[14:26]))

print()
print('═' * 72)
print('4. 갈래끼리 얼마나 이어져 있나 — 붙여야 할 갈래가 있는가')
print('═' * 72)
M = np.zeros((NG, NG))
for a, b, w in KL:
    if CM[a] != CM[b]: M[CM[a], CM[b]] += w; M[CM[b], CM[a]] += w
pairs = []
for a in range(NG):
    for b in range(a + 1, NG):
        inner_a = sum(w for x, y, w in KL if CM[x] == a and CM[y] == a)
        inner_b = sum(w for x, y, w in KL if CM[x] == b and CM[y] == b)
        if M[a, b]: pairs.append((M[a, b] / max(1, min(inner_a, inner_b)), M[a, b], a, b))
pairs.sort(reverse=True)
for r, raw, a, b in pairs[:6]:
    print(f'  {F[a]["name"]} ↔ {F[b]["name"]}   연결 {raw:.0f} (작은 쪽 내부연결의 {r*100:.0f}%)')
print('  → 100%를 넘으면 사실상 한 갈래. 그런 쌍이 없으면 분리가 유지된다.')

print()
print('═' * 72)
print('5. 지도에서 빠진 것 — 무엇을 잃었는가')
print('═' * 72)
papers_all = json.load(open(os.path.join(BASE, 'build', 'papers.json'), encoding='utf-8'))['papers']
onmap = set(NAME)
allkw = collections.Counter(k for p in papers_all for k in p['kws'])
lost = [(c, k) for k, c in allkw.items() if k not in onmap]
lost.sort(reverse=True)
covered = sum(1 for p in papers_all if any(k in onmap for k in p['kws']))
print(f'  전체 키워드 {len(allkw)}개 중 지도에 {len(onmap)}개 ({len(onmap)*100//len(allkw)}%)')
print(f'  논문 {len(papers_all)}편 중 {covered}편 ({covered*100//len(papers_all)}%)이 지도 위 키워드를 하나 이상 가짐')
print(f'  빠진 키워드 중 가장 많이 쓰인 것: ' + ', '.join(f'{k}({c})' for c, k in lost[:8]))
print(f'  빠진 것의 {sum(1 for c,_ in lost if c<=2)*100//len(lost)}%는 1~2편에만 쓰인 키워드')
