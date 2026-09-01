# -*- coding: utf-8 -*-
"""template.html 의 /*__DATA__*/ 자리에 graph.json 을 끼워 costume-graph.html 생성"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = open(os.path.join(BASE, 'build', 'template.html'), encoding='utf-8').read()
data = open(os.path.join(BASE, 'build', 'graph.json'), encoding='utf-8').read()

MARK = '/*__DATA__*/'
assert MARK in tpl, 'template.html 에 /*__DATA__*/ 자리표시자가 없습니다'

out = os.path.join(BASE, 'costume-graph.html')
open(out, 'w', encoding='utf-8').write(tpl.replace(MARK, data))
print(f'{out}  {os.path.getsize(out)/1024:.0f} KB')
