# -*- coding: utf-8 -*-
"""연구 갈래(군집)를 찾아 그래프에 붙인다. 색이 아니라 '위치'로 표현할 값."""
import json, os, re, networkx as nx
from networkx.algorithms.community import louvain_communities

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G_ = json.load(open(os.path.join(BASE, 'build', 'graph.json'), encoding='utf-8'))
N, L, NP = G_['nodes'], G_['links'], G_['nPapers']

g = nx.Graph(); g.add_nodes_from(range(len(N)))
for s, t, typ in L:
    g.add_edge(s, t, weight=1.0 if typ == 0 else 0.45)

comms = louvain_communities(g, weight='weight', resolution=0.35, seed=7)
comms.sort(key=len, reverse=True)
TOP = 8
main, other = comms[:TOP], comms[TOP:]

# 갈래 이름은 그 군집에서 가장 많이 쓰인 키워드에서 직접 뽑는다.
# 군집 번호는 실행마다 흔들릴 수 있으므로 이름을 순서에 묶어두지 않는다.
def name_of(kws):
    picked, seen = [], set()
    for k in kws:
        base = re.sub(r'\s+', '', k)
        if any(base in s2 or s2 in base for s2 in seen):   # 겹치는 말(패션/패션디자인)은 하나만
            continue
        seen.add(base); picked.append(k)
        if len(picked) == 2:
            break
    return ' · '.join(picked) if picked else '기타'

label = [TOP] * len(N)
for ci, c in enumerate(main):
    for v in c:
        label[v] = ci

info = []
for ci in range(TOP):
    kws = sorted(((N[i][3], N[i][1]) for i in range(NP, len(N)) if label[i] == ci and N[i][0] == 1), reverse=True)
    info.append({'name': name_of([k for _, k in kws]),
                 'papers': sum(1 for i in range(NP) if label[i] == ci),
                 'top': [k for _, k in kws[:5]]})
info.append({'name': '그 외', 'papers': sum(1 for i in range(NP) if label[i] == TOP), 'top': []})

for i, d in enumerate(info):
    print(f"  [{i}] {d['name']:<22} 논문 {d['papers']:4d}편   {' · '.join(d['top'])}")
cov = sum(len(c) for c in main)
print(f'\n상위 {TOP}개 갈래가 {cov}/{len(N)} 노드 ({cov*100//len(N)}%)를 덮음')

# ── 갈래 자리: 갈래끼리의 연결 세기로 배치하고, 크기에 비례해 간격을 준다 ──
meta = nx.Graph()
meta.add_nodes_from(range(TOP))
w = {}
for s_, t_, _ in L:
    a, b = label[s_], label[t_]
    if a != b and a < TOP and b < TOP:
        w[(min(a, b), max(a, b))] = w.get((min(a, b), max(a, b)), 0) + 1
for (a, b), c in w.items():
    meta.add_edge(a, b, weight=c)

size = [sum(1 for i in range(len(N)) if label[i] == g) for g in range(TOP)]
pos = nx.spring_layout(meta, weight='weight', seed=3, iterations=600, k=1.9)
xs = [pos[g][0] for g in range(TOP)]; ys = [pos[g][1] for g in range(TOP)]
cx0, cy0 = sum(xs) / TOP, sum(ys) / TOP
span = max(max(abs(x - cx0) for x in xs), max(abs(y - cy0) for y in ys)) or 1
SCALE = 900 / span
anchors = [[round((pos[g][0] - cx0) * SCALE, 1), round((pos[g][1] - cy0) * SCALE, 1)] for g in range(TOP)]
anchors.append([0.0, 0.0])                      # '그 외'는 한가운데

# 갈래가 서로 겹치지 않게 반지름만큼 밀어낸다
rad = [28 * (s2 ** 0.5) for s2 in size] + [0]
for _ in range(300):
    for a in range(TOP):
        for b in range(a + 1, TOP):
            dx = anchors[b][0] - anchors[a][0]; dy = anchors[b][1] - anchors[a][1]
            d = (dx * dx + dy * dy) ** 0.5 or 1
            need = (rad[a] + rad[b]) * 0.95
            if d < need:
                push = (need - d) / 2 / d
                anchors[a][0] -= dx * push; anchors[a][1] -= dy * push
                anchors[b][0] += dx * push; anchors[b][1] += dy * push

print('\n갈래 자리 (노드수 / 반경 / 좌표)')
for g in range(TOP):
    print(f'  [{g}] {info[g]["name"]:<24} {size[g]:4d}  r={rad[g]:5.0f}  ({anchors[g][0]:7.0f},{anchors[g][1]:7.0f})')

G_['anchors'] = anchors
G_['comm'] = label
G_['fields'] = info
G_['nFields'] = TOP
json.dump(G_, open(os.path.join(BASE, 'build', 'graph.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print('graph.json 갱신')
