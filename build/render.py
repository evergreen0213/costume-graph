# -*- coding: utf-8 -*-
"""template.html 의 /*__DATA__*/ 자리에 view-<design>.json 을 넣어 완성본을 만든다."""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN = sys.argv[sys.argv.index('--design') + 1] if '--design' in sys.argv else 'bojagi'
SUFFIX = {'bojagi': '', 'hyungbae': '-2-hyungbae', 'chaekgado': '-3-chaekgado',
          'saekdong': '-4-saekdong', 'hanbok': '-5-hanbok', 'tal': '-6-tal',
          'wanja': '-7-wanja', 'mugunghwa': '-8-mugunghwa',
          'hanok': '-9-hanok'}[DESIGN]

# 자기 갱신을 켤 주소. 비어 있으면 페이지는 품고 있는 자료로만 돈다.
#   PAGES_URL=https://<계정>.github.io/costume-graph python3 build/render.py --design bojagi
PAGES_URL = os.environ.get('PAGES_URL', '').strip().rstrip('/')
if PAGES_URL and not PAGES_URL.startswith('https://'):
    raise SystemExit('PAGES_URL 은 https:// 로 시작해야 한다 — ' + PAGES_URL)

tpl = open(os.path.join(BASE, 'build', 'template.html'), encoding='utf-8').read()
data = json.load(open(os.path.join(BASE, 'build', f'view-{DESIGN}.json'), encoding='utf-8'))
html = tpl.replace('/*__DATA__*/', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
html = html.replace('/*__PAGES_URL__*/', PAGES_URL)
for ph in ('/*__DATA__*/', '/*__PAGES_URL__*/'):
    if ph in html:
        raise SystemExit(f'자리표시자가 치환되지 않았다: {ph}')

out = os.path.join(BASE, f'costume-graph{SUFFIX}.html')
open(out, 'w', encoding='utf-8').write(html)

# 페이지가 받아 갈 자료와 판 번호. html 과 나란히 둔다.
json.dump(data, open(os.path.join(BASE, f'costume-graph{SUFFIX}.data.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
json.dump({'build': data.get('build'), 'builtAt': data.get('builtAt'), 'design': DESIGN},
          open(os.path.join(BASE, f'costume-graph{SUFFIX}.version.json'), 'w', encoding='utf-8'),
          ensure_ascii=False)
print(f"{DESIGN:<10} {data['designLabel']:<7} -> {os.path.basename(out)}  {os.path.getsize(out)/1024:.0f} KB")
