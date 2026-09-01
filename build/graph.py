# -*- coding: utf-8 -*-
"""papers.json -> 그래프(노드/링크) + 임베드용 압축 페이로드"""
import json, collections, os, math, random

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KW_MIN = 2      # 키워드 노드로 승격할 최소 등장 논문 수
AU_MIN = 2      # 저자 노드로 승격할 최소 논문 수

papers = json.load(open(os.path.join(BASE, 'build', 'papers.json'), encoding='utf-8'))['papers']

kw_count = collections.Counter(k for p in papers for k in p['kws'])
au_count = collections.Counter(a for p in papers for a in p['authors'])
kw_keep = {k for k, c in kw_count.items() if c >= KW_MIN}
au_keep = {a for a, c in au_count.items() if c >= AU_MIN}

# --- 노드 배열 (타입 0=논문 1=키워드 2=저자) ---
nodes, index = [], {}
for p in papers:
    index[p['id']] = len(nodes)
    nodes.append([0, p['title'], p['year'], p['cites']])
kw_ids = {}
for k in sorted(kw_keep, key=lambda x: -kw_count[x]):
    kw_ids[k] = len(nodes)
    nodes.append([1, k, 0, kw_count[k]])
au_ids = {}
for a in sorted(au_keep, key=lambda x: -au_count[x]):
    au_ids[a] = len(nodes)
    nodes.append([2, a, 0, au_count[a]])

# --- 링크 (0=논문-키워드, 1=논문-저자) ---
links = []
for p in papers:
    s = index[p['id']]
    for k in p['kws']:
        if k in kw_ids:
            links.append([s, kw_ids[k], 0])
    for a in p['authors']:
        if a in au_ids:
            links.append([s, au_ids[a], 1])

# --- 논문 메타 (상세 패널용) ---
meta = [[p['authors'], p['affil'] or '', p['vol'] or 0, p['iss'] or 0,
         p['sp'] or 0, p['ep'] or 0, p['kws']] for p in papers]

deg = collections.Counter()
for s, t, _ in links:
    deg[s] += 1; deg[t] += 1
iso = sum(1 for i in range(len(papers)) if deg[i] == 0)

out = {'nodes': nodes, 'links': links, 'meta': meta, 'nPapers': len(papers)}
path = os.path.join(BASE, 'build', 'graph.json')
json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

print(f'노드 {len(nodes)}  (논문 {len(papers)} / 키워드 {len(kw_ids)} / 저자 {len(au_ids)})')
print(f'링크 {len(links)}  (논문-키워드 {sum(1 for l in links if l[2]==0)} / 논문-저자 {sum(1 for l in links if l[2]==1)})')
print(f'고립 논문 {iso}')
print(f'{path}  {os.path.getsize(path)/1024:.0f} KB')
