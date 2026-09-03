# -*- coding: utf-8 -*-
"""지도를 담는 아홉 가지 틀.

데이터와 파이프라인은 하나다. 이 파일이 바꾸는 것은 셋뿐이다.
  frame   바깥 테두리 (천 자락 / 흉배 / 고리 / 격자 전체)
  regions 갈래마다 정해진 구역. None 이면 자리를 데이터가 잡는다(유기적 배치).
  decor   그 디자인 고유의 장식. 그리기 명령 목록으로 넘긴다.

decor 명령:
  {'t':'poly',   'pts':[[x,y]..], 'stroke':색, 'w':굵기, 'a':투명도, 'dash':[..], 'fill':색}
  {'t':'line',   'pts':[[x,y],[x,y]], ...}
  {'t':'circle', 'c':[x,y], 'r':반지름, 'fill':색, 'stroke':색, ...}
  색 이름: ink ink2 ink3 brand panel ground edge  (화면 쪽 색 토큰)
"""
import math

R = 1250.0                      # 기준 반지름 — 모든 틀이 이 안에 들어온다


# ── 공통 도형 ─────────────────────────────────────────────────────────
def _rounded_square(half, corner, wobble=0.0, waves=2.0, per_side=40, per_corner=12, phase=0.0):
    C = corner
    sides = [((0, -1), (1, 0), (0, -1)), ((1, 0), (0, 1), (1, 0)),
             ((0, 1), (-1, 0), (0, 1)), ((-1, 0), (0, -1), (-1, 0))]
    sign = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
    pts = []
    for i, ((ax, ay), (dx, dy), (nx, ny)) in enumerate(sides):
        sx, sy = sign[i]; px, py = sign[i - 1]
        x0 = ax if ax else px * (1 - C); y0 = ay if ay else py * (1 - C)
        x1 = ax if ax else sx * (1 - C); y1 = ay if ay else sy * (1 - C)
        for j in range(per_side):
            t = j / per_side
            w = math.sin(t * math.pi) * math.sin(t * math.pi * waves + i * 1.9 + phase) * wobble
            pts.append(((x0 + (x1 - x0) * t + nx * w) * half,
                        (y0 + (y1 - y0) * t + ny * w) * half))
        cx, cy = sx * (1 - C), sy * (1 - C)
        a0 = math.radians(i * 90 - 90)
        for j in range(per_corner + 1):
            a = a0 + math.radians(90) * j / per_corner
            pts.append(((cx + math.cos(a) * C) * half, (cy + math.sin(a) * C) * half))
    return [(round(x, 2), round(y, 2)) for x, y in pts]


def _ring_sector(a0, a1, r0, r1, steps=26):
    pts = [(math.cos(a0 + (a1 - a0) * i / steps) * r1,
            math.sin(a0 + (a1 - a0) * i / steps) * r1) for i in range(steps + 1)]
    pts += [(math.cos(a1 - (a1 - a0) * i / steps) * r0,
             math.sin(a1 - (a1 - a0) * i / steps) * r0) for i in range(steps + 1)]
    return [(round(x, 2), round(y, 2)) for x, y in pts]


def _rect(x0, y0, x1, y1):
    return [(round(x0, 2), round(y0, 2)), (round(x1, 2), round(y0, 2)),
            (round(x1, 2), round(y1, 2)), (round(x0, 2), round(y1, 2))]


# ── 1안 조각보 ────────────────────────────────────────────────────────
def _bojagi():
    cloth = _rounded_square(R, 0.13, wobble=0.020)
    hem = [(x * 0.963, y * 0.963) for x, y in cloth]
    d = 1 - 0.13 * 0.55
    decor = [{'t': 'poly', 'pts': hem, 'stroke': 'ink', 'w': 1.3, 'a': .38,
              'dash': [9, 6], 'close': True}]
    for px, py in ((-d, -d), (d, -d), (d, d), (-d, d)):        # 네 모서리 고름
        nx, ny = px / abs(px), py / abs(py)
        ax, ay = px * R, py * R
        decor.append({'t': 'line', 'pts': [[ax, ay], [ax + nx * 130, ay + ny * 130]],
                      'stroke': 'brand', 'w': 4.4, 'cap': 'round'})
        decor.append({'t': 'circle', 'c': [ax + nx * 82, ay + ny * 82], 'r': 11, 'fill': 'brand'})
    return {'frame': cloth, 'regions': None, 'decor': decor, 'inset': 1.0}


# ── 2안 흉배 ──────────────────────────────────────────────────────────
def _hyungbae():
    outer = _rounded_square(R, 0.035)
    band_in = _rounded_square(R * 0.855, 0.04)
    inner = _rounded_square(R * 0.80, 0.05)
    decor = [{'t': 'poly', 'pts': outer, 'stroke': 'ink', 'w': 3.4, 'a': .72, 'close': True},
             {'t': 'poly', 'pts': band_in, 'stroke': 'ink', 'w': 2.0, 'a': .55, 'close': True},
             {'t': 'poly', 'pts': inner, 'stroke': 'ink', 'w': 1.6, 'a': .42, 'close': True}]
    # 테두리 띠에 두르는 운문 — 둥근 구름이 이어지는 무늬
    steps = 68
    for i in range(steps):
        t = i / steps * 2 * math.pi
        rr = R * 0.928
        cx, cy = math.cos(t) * rr, math.sin(t) * rr
        m = max(abs(cx), abs(cy)) or 1
        cx, cy = cx / m * rr, cy / m * rr                      # 정사각 테두리 위로 투영
        decor.append({'t': 'circle', 'c': [round(cx, 1), round(cy, 1)], 'r': 17,
                      'stroke': 'ink', 'w': 1.5, 'a': .30})
    # 아래쪽 파도문 — 흉배 하단의 바다
    for row, amp in ((0.965, 26), (0.995, 20)):
        pts = []
        for i in range(41):
            x = -R * 0.80 + (R * 1.60) * i / 40
            pts.append([round(x, 1), round(R * row - math.sin(i / 40 * math.pi * 7) * amp, 1)])
        decor.append({'t': 'path', 'pts': pts, 'stroke': 'ink', 'w': 1.5, 'a': .34})
    return {'frame': inner, 'regions': None, 'decor': decor, 'inset': 0.80}


# ── 3안 책가도 ────────────────────────────────────────────────────────
def _chaekgado(NG):
    cols = 5 if NG % 5 == 0 else 4
    rows = math.ceil(NG / cols)
    gap = R * 0.028
    W, H = R * 2 * 0.99, R * 2 * 0.86
    x0, y0 = -W / 2, -H / 2
    cw, ch = W / cols, H / rows
    slots = []
    for r in range(rows):
        n = min(cols, NG - r * cols)
        span = W / n                                   # 남은 칸이 적으면 그 줄만 넓게 나눈다
        for c in range(n):
            slots.append((x0 + c * span + gap, y0 + r * ch + gap,
                          x0 + (c + 1) * span - gap, y0 + (r + 1) * ch - gap))
    regions = [_rect(*s_) for s_ in slots[:NG]]
    out = _rect(x0 - gap * 2.4, y0 - gap * 2.4, x0 + W + gap * 2.4, y0 + H + gap * 2.4)
    decor = [{'t': 'poly', 'pts': out, 'stroke': 'ink', 'w': 3.6, 'a': .70, 'close': True}]
    for r in range(1, rows):                           # 시렁 — 가로 선반
        y = y0 + r * ch
        decor.append({'t': 'line', 'pts': [[x0 - gap * 2.4, y], [x0 + W + gap * 2.4, y]],
                      'stroke': 'ink', 'w': 3.2, 'a': .58})
    for s_ in slots[:NG]:
        decor.append({'t': 'poly', 'pts': _rect(*s_), 'stroke': 'ink', 'w': 1.4, 'a': .32, 'close': True})
    return {'frame': out, 'regions': regions, 'decor': decor, 'inset': 1.0}


# ── 4안 색동 고리 ─────────────────────────────────────────────────────
def _saekdong(NG):
    r0, r1 = R * 0.40, R * 0.99
    pad = math.radians(1.1)
    regions, decor = [], []
    for gi in range(NG):
        a0 = -math.pi / 2 + 2 * math.pi * gi / NG + pad
        a1 = -math.pi / 2 + 2 * math.pi * (gi + 1) / NG - pad
        regions.append(_ring_sector(a0, a1, r0, r1))
        decor.append({'t': 'poly', 'pts': regions[-1], 'stroke': 'ink', 'w': 1.5, 'a': .34, 'close': True})
    ring = [(math.cos(a * math.pi / 90) * r1, math.sin(a * math.pi / 90) * r1) for a in range(180)]
    hole = [(math.cos(a * math.pi / 90) * r0, math.sin(a * math.pi / 90) * r0) for a in range(180)]
    decor.insert(0, {'t': 'poly', 'pts': [[round(x, 1), round(y, 1)] for x, y in ring],
                     'stroke': 'ink', 'w': 3.2, 'a': .68, 'close': True})
    decor.append({'t': 'poly', 'pts': [[round(x, 1), round(y, 1)] for x, y in hole],
                  'stroke': 'ink', 'w': 2.4, 'a': .55, 'close': True})
    return {'frame': [[round(x, 1), round(y, 1)] for x, y in ring],
            'regions': regions, 'decor': decor, 'inset': 1.0}




# ── 공통: 모서리 눕히기 ───────────────────────────────────────────────
def _chaikin(poly, it=2):
    pts = [tuple(q) for q in poly]
    for _ in range(it):
        out = []
        m = len(pts)
        for i in range(m):
            a, b = pts[i], pts[(i + 1) % m]
            out.append((a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25))
            out.append((a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75))
        pts = out
    return [(round(x, 2), round(y, 2)) for x, y in pts]


# ── 5안 한복 ──────────────────────────────────────────────────────────
def _hanbok():
    """저고리와 치마. 소매가 벌어지고 치마가 퍼진다."""
    p = [(-0.15, -0.99), (0.15, -0.99), (0.31, -0.94),
         (0.97, -0.87), (1.00, -0.62), (0.37, -0.54),          # 오른 소매
         (0.35, -0.33),                                        # 허리
         (0.72, 0.42), (0.90, 0.88), (0.74, 0.99),             # 치마 오른자락
         (-0.74, 0.99), (-0.90, 0.88), (-0.72, 0.42),          # 치마 왼자락
         (-0.35, -0.33), (-0.37, -0.54),
         (-1.00, -0.62), (-0.97, -0.87), (-0.31, -0.94)]
    frame = [(x * R, y * R) for x, y in _chaikin(p, 2)]
    decor = []
    # 깃 — 목을 감싸 여미는 선
    decor.append({'t': 'path', 'pts': [[-0.15 * R, -0.99 * R], [0.0, -0.62 * R], [0.15 * R, -0.99 * R]],
                  'stroke': 'ink', 'w': 3.0, 'a': .58})
    decor.append({'t': 'path', 'pts': [[-0.09 * R, -0.99 * R], [0.0, -0.72 * R], [0.09 * R, -0.99 * R]],
                  'stroke': 'ink', 'w': 1.8, 'a': .40})
    # 고름 — 붉은 옷고름 두 자락
    decor.append({'t': 'path', 'pts': [[0.02 * R, -0.63 * R], [-0.07 * R, -0.30 * R], [-0.05 * R, 0.02 * R]],
                  'stroke': 'brand', 'w': 5.0, 'a': .85, 'cap': 'round'})
    decor.append({'t': 'path', 'pts': [[0.02 * R, -0.63 * R], [0.10 * R, -0.34 * R], [0.06 * R, -0.06 * R]],
                  'stroke': 'brand', 'w': 5.0, 'a': .85, 'cap': 'round'})
    # 저고리 밑단 — 치마와 나뉘는 자리
    decor.append({'t': 'path', 'pts': [[-0.35 * R, -0.33 * R], [0, -0.29 * R], [0.35 * R, -0.33 * R]],
                  'stroke': 'ink', 'w': 2.2, 'a': .42, 'dash': [11, 8]})
    # 치마 주름
    for f in (-0.52, -0.26, 0.0, 0.26, 0.52):
        decor.append({'t': 'path', 'pts': [[f * 0.36 * R, -0.28 * R], [f * 0.92 * R, 0.94 * R]],
                      'stroke': 'ink', 'w': 1.3, 'a': .20})
    return {'frame': frame, 'regions': None, 'decor': decor, 'inset': 1.0}


# ── 6안 탈 ────────────────────────────────────────────────────────────
def _tal():
    """하회탈 양반. 이마가 넓고 턱으로 갈수록 좁아진다."""
    p = []
    for i in range(46):
        a = -math.pi / 2 + 2 * math.pi * i / 46
        c, s_ = math.cos(a), math.sin(a)
        rx = 0.80 + 0.05 * max(0.0, -s_)                  # 위가 조금 더 넓다
        ry = 0.99 if s_ < 0 else 1.00
        k = 1.0 - 0.30 * max(0.0, s_) ** 1.7               # 턱으로 갈수록 좁아진다
        p.append((c * rx * k, s_ * ry))
    frame = [(x * R, y * R) for x, y in _chaikin(p, 1)]
    decor = []
    # 이마선
    decor.append({'t': 'path', 'pts': [[-0.62 * R, -0.52 * R], [0, -0.76 * R], [0.62 * R, -0.52 * R]],
                  'stroke': 'ink', 'w': 6.0, 'a': .72})
    for sx in (-1, 1):
        # 눈썹
        decor.append({'t': 'path',
                      'pts': [[sx * 0.14 * R, -0.34 * R], [sx * 0.36 * R, -0.46 * R], [sx * 0.60 * R, -0.34 * R]],
                      'stroke': 'ink', 'w': 9.0, 'a': .78, 'cap': 'round'})
        # 눈 — 초승달처럼 휜 구멍
        eye = [[sx * 0.18 * R, -0.20 * R], [sx * 0.36 * R, -0.30 * R], [sx * 0.56 * R, -0.19 * R],
               [sx * 0.36 * R, -0.11 * R]]
        decor.append({'t': 'poly', 'pts': eye, 'close': True, 'stroke': 'ink', 'w': 5.0, 'a': .76,
                      'fill': 'ground'})
        # 광대 주름
        decor.append({'t': 'path', 'pts': [[sx * 0.20 * R, 0.02 * R], [sx * 0.46 * R, 0.10 * R]],
                      'stroke': 'ink', 'w': 3.2, 'a': .48})
    # 코
    decor.append({'t': 'path', 'pts': [[0, -0.26 * R], [-0.09 * R, 0.16 * R], [0, 0.22 * R], [0.09 * R, 0.16 * R]],
                  'stroke': 'ink', 'w': 5.0, 'a': .70})
    # 입 — 웃는 입
    decor.append({'t': 'poly',
                  'pts': [[-0.34 * R, 0.42 * R], [0, 0.36 * R], [0.34 * R, 0.42 * R],
                          [0.20 * R, 0.62 * R], [-0.20 * R, 0.62 * R]],
                  'close': True, 'stroke': 'ink', 'w': 5.6, 'a': .76, 'fill': 'ground'})
    return {'frame': frame, 'regions': None, 'decor': decor, 'inset': 1.0}


# ── 7안 완자창 ────────────────────────────────────────────────────────
def _wanja(NG):
    """팔각 창에 완자살. 창살이 나눈 칸이 곧 갈래의 자리."""
    cut = 0.30
    oct_ = [(-1 + cut, -1), (1 - cut, -1), (1, -1 + cut), (1, 1 - cut),
            (1 - cut, 1), (-1 + cut, 1), (-1, 1 - cut), (-1, -1 + cut)]
    frame = [(x * R, y * R) for x, y in oct_]
    from shapely.geometry import Polygon as _P
    oct_poly = _P(frame)

    cols, rows = 4, 3
    W = H = 2 * R
    cw, ch = W / cols, H / rows
    cand = []
    for r in range(rows):
        for c in range(cols):
            cell = _P([(-R + c * cw, -R + r * ch), (-R + (c + 1) * cw, -R + r * ch),
                       (-R + (c + 1) * cw, -R + (r + 1) * ch), (-R + c * cw, -R + (r + 1) * ch)])
            q = cell.intersection(oct_poly).buffer(-R * 0.016)
            if q.is_empty: continue
            if q.geom_type != 'Polygon': q = max(q.geoms, key=lambda z: z.area)
            cand.append((q.area, [[round(x, 1), round(y, 1)] for x, y in q.exterior.coords[:-1]]))
    cand.sort(key=lambda t: -t[0])
    regions = [c[1] for c in cand[:NG]]

    decor = [{'t': 'poly', 'pts': frame, 'stroke': 'ink', 'w': 5.0, 'a': .78, 'close': True},
             {'t': 'poly', 'pts': [(x * 0.94, y * 0.94) for x, y in frame],
              'stroke': 'ink', 'w': 2.2, 'a': .42, 'close': True}]
    for r_ in regions:                                   # 창살 — 칸을 두르는 살
        decor.append({'t': 'poly', 'pts': r_, 'stroke': 'ink', 'w': 2.6, 'a': .46, 'close': True})
    # 완자(卍) 무늬 — 칸 사이 살이 만나는 자리에
    for r in range(1, rows):
        for c in range(1, cols):
            x, y = -R + c * cw, -R + r * ch
            if not oct_poly.contains(_P([(x - 30, y - 30), (x + 30, y - 30), (x + 30, y + 30), (x - 30, y + 30)])):
                continue
            u = R * 0.036
            decor.append({'t': 'path', 'pts': [[x - u * 2, y - u], [x, y - u], [x, y - u * 2]],
                          'stroke': 'ink', 'w': 2.0, 'a': .40})
            decor.append({'t': 'path', 'pts': [[x + u * 2, y + u], [x, y + u], [x, y + u * 2]],
                          'stroke': 'ink', 'w': 2.0, 'a': .40})
    return {'frame': frame, 'regions': regions, 'decor': decor, 'inset': 1.0}


# ── 8안 무궁화 ────────────────────────────────────────────────────────
def _petal(a0, a1, r0, r1, steps=26):
    """밑이 좁고 가운데가 넓다가 끝이 둥근 꽃잎."""
    mid = (a0 + a1) / 2
    half = (a1 - a0) / 2 * 1.30
    left, right = [], []
    for i in range(steps + 1):
        t = i / steps
        w = math.sin(math.pi * (t ** 0.50)) ** 0.75 * half
        r = r0 + (r1 - r0) * t
        left.append((math.cos(mid - w) * r, math.sin(mid - w) * r))
        right.append((math.cos(mid + w) * r, math.sin(mid + w) * r))
    return [(round(x, 2), round(y, 2)) for x, y in left + right[::-1]]


def _mugunghwa(NG):
    """무궁화. 꽃잎마다 갈래 하나, 가운데는 붉은 단심."""
    r0, r1 = R * 0.30, R * 1.0
    regions = [_petal(-math.pi / 2 + 2 * math.pi * gi / NG,
                      -math.pi / 2 + 2 * math.pi * (gi + 1) / NG, r0, r1) for gi in range(NG)]
    frame = []
    for r_ in regions:
        frame += r_[:len(r_) // 2]                        # 바깥 윤곽만 이어 붙인다
    decor = [{'t': 'poly', 'pts': r_, 'stroke': 'ink', 'w': 2.4, 'a': .44, 'close': True} for r_ in regions]
    # 단심 — 무궁화 한가운데의 붉은 자리
    decor.append({'t': 'circle', 'c': [0, 0], 'r': r0 * 0.95, 'fill': 'brand', 'a': .16})
    decor.append({'t': 'circle', 'c': [0, 0], 'r': r0 * 0.95, 'stroke': 'brand', 'w': 3.0, 'a': .62})
    for i in range(NG):                                   # 단심에서 뻗는 붉은 맥
        a = -math.pi / 2 + 2 * math.pi * (i + 0.5) / NG
        decor.append({'t': 'path',
                      'pts': [[math.cos(a) * r0 * 0.9, math.sin(a) * r0 * 0.9],
                              [math.cos(a) * r0 * 1.55, math.sin(a) * r0 * 1.55]],
                      'stroke': 'brand', 'w': 2.6, 'a': .45, 'cap': 'round'})
    decor.append({'t': 'circle', 'c': [0, 0], 'r': r0 * 0.30, 'fill': 'brand', 'a': .5})
    return {'frame': frame, 'regions': regions, 'decor': decor, 'inset': 1.0}


# ── 9안 한옥 ──────────────────────────────────────────────────────────
def _eave(x):
    """처마 밑선. 가운데는 낮고 추녀 쪽으로 갈수록 치켜올라간다."""
    return -0.115 - 0.34 * abs(x) ** 3.6


def _roof(x):
    """지붕 윗면. 용마루에서 흘러내리다가 추녀 끝에서 처마를 따라 함께 들린다."""
    main = -0.88 + 0.52 * (max(0.0, abs(x) - 0.30) / 0.70) ** 1.45
    w = min(1.0, max(0.0, (abs(x) - 0.70) / 0.30)) ** 2      # 끝으로 갈수록 처마를 따른다
    return main * (1 - w) + (_eave(x) - 0.10) * w


def _densify(p, step=0.045):
    """곧은 자리에도 점을 심는다. 그래야 _chaikin 이 모서리만 눕히고 변은 펴 둔다."""
    out = []
    for i in range(len(p)):
        (x0, y0), (x1, y1) = p[i], p[(i + 1) % len(p)]
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * t / n) for t in range(n)]
    return out


def _hanok():
    """한옥 정면. 지붕이 넓게 뻗고 추녀 끝이 들린다."""
    RID, EDG, COL_, BASE = 0.30, 1.00, 0.62, 0.60         # 용마루 · 추녀 · 기둥 · 마루
    xs = [RID + (EDG - RID) * i / 22 for i in range(23)]
    p = [(-RID, -0.88), (RID, -0.88)]
    p += [(x, _roof(x)) for x in xs[1:]]                  # 오른 지붕면
    p += [(x, _eave(x)) for x in xs[::-1] if x >= COL_]   # 추녀 끝을 돌아 처마 밑으로
    p += [(COL_, BASE), (0.87, 0.62), (0.88, 0.90),       # 오른 기둥 · 기단
          (-0.88, 0.90), (-0.87, 0.62), (-COL_, BASE)]
    p += [(-x, _eave(x)) for x in xs if x >= COL_]        # 왼 처마 밑
    p += [(-x, _roof(x)) for x in xs[::-1][:-1]]          # 왼 지붕면
    frame = [(x * R, y * R) for x, y in _chaikin(_densify(p), 1)]

    decor = []
    # 기와골 — 용마루에서 처마로 흘러내리는 기왓장 줄. 끝으로 갈수록 부챗살처럼 벌어진다.
    for i in range(21):
        u = -1 + 2 * i / 20
        xt, xb = u * 0.78, u * 0.955                      # 위는 모이고 아래로 벌어진다
        yt = -0.88 if abs(xt) <= RID else _roof(xt)
        yb = _eave(xb) - 0.045
        pts = []
        for j in range(9):
            t = j / 8
            x = xt + (xb - xt) * t
            y = yt + (yb - yt) * t + math.sin(math.pi * t) * 0.045  # 지붕면이 오목하게 팬다
            pts.append([round(x * R, 1), round(y * R, 1)])
        decor.append({'t': 'path', 'pts': pts, 'stroke': 'ink', 'w': 1.6, 'a': .24})

    # 용마루 — 지붕 꼭대기의 두꺼운 마루
    decor.append({'t': 'path', 'pts': [[-0.345 * R, -0.885 * R], [0.345 * R, -0.885 * R]],
                  'stroke': 'ink', 'w': 9.0, 'a': .78, 'cap': 'round'})
    decor.append({'t': 'path', 'pts': [[-0.33 * R, -0.845 * R], [0.33 * R, -0.845 * R]],
                  'stroke': 'ink', 'w': 2.0, 'a': .36})
    for sx in (-1, 1):                                    # 망와 — 마루 끝을 막는 기와
        decor.append({'t': 'circle', 'c': [sx * 0.345 * R, -0.885 * R], 'r': 21,
                      'fill': 'ink', 'a': .60})

    # 부연 — 처마 끝을 한 겹 더 두른 선 (겹처마)
    e2 = [[round(x * R, 1), round((_eave(x) - 0.038) * R, 1)]
          for x in [-0.99 + 1.98 * i / 60 for i in range(61)]]
    decor.append({'t': 'path', 'pts': e2, 'stroke': 'ink', 'w': 2.4, 'a': .40})
    # 서까래 — 처마 밑으로 내민 나무 끝
    for i in range(26):
        u = -1 + 2 * i / 25
        x = u * 0.955
        decor.append({'t': 'path',
                      'pts': [[round(x * R, 1), round((_eave(x) - 0.038) * R, 1)],
                              [round(x * R, 1), round(_eave(x) * R, 1)]],
                      'stroke': 'ink', 'w': 2.4, 'a': .28})

    # 창방 단청 — 기둥 위를 가로지르는 붉은 띠
    decor.append({'t': 'path', 'pts': [[-0.63 * R, -0.07 * R], [0.63 * R, -0.07 * R]],
                  'stroke': 'brand', 'w': 6.5, 'a': .58, 'cap': 'round'})

    # 기둥 — 정면 세 칸을 만드는 네 기둥
    for f in (-0.62, -0.21, 0.21, 0.62):
        decor.append({'t': 'path', 'pts': [[f * R, -0.075 * R], [f * R, BASE * R]],
                      'stroke': 'ink', 'w': 4.4, 'a': .24})
        decor.append({'t': 'circle', 'c': [f * R, (BASE + 0.016) * R], 'r': 17,   # 주춧돌
                      'stroke': 'ink', 'w': 2.4, 'a': .40})
        decor.append({'t': 'circle', 'c': [f * R, -0.07 * R], 'r': 9, 'fill': 'brand', 'a': .55})

    # 마루 — 몸채와 기단이 나뉘는 자리
    decor.append({'t': 'path', 'pts': [[-0.63 * R, BASE * R], [0.63 * R, BASE * R]],
                  'stroke': 'ink', 'w': 3.4, 'a': .50})
    # 기단 — 돌을 두 켜로 쌓았다
    decor.append({'t': 'path', 'pts': [[-0.875 * R, 0.63 * R], [0.875 * R, 0.63 * R]],
                  'stroke': 'ink', 'w': 3.0, 'a': .52})
    decor.append({'t': 'path', 'pts': [[-0.878 * R, 0.775 * R], [0.878 * R, 0.775 * R]],
                  'stroke': 'ink', 'w': 1.8, 'a': .28, 'dash': [14, 10]})
    # 섬돌 — 가운데 칸 앞의 디딤돌
    decor.append({'t': 'poly', 'pts': _rect(-0.20 * R, 0.885 * R, 0.20 * R, 0.975 * R),
                  'stroke': 'ink', 'w': 2.6, 'a': .46, 'close': True})
    return {'frame': frame, 'regions': None, 'decor': decor, 'inset': 1.0}


DESIGNS = {
    'bojagi':    ('조각보',    _bojagi),
    'hyungbae':  ('흉배',      _hyungbae),
    'chaekgado': ('책가도',    _chaekgado),
    'saekdong':  ('색동 고리',  _saekdong),
    'hanbok':    ('한복',      _hanbok),
    'tal':       ('하회탈',    _tal),
    'wanja':     ('완자창',    _wanja),
    'mugunghwa': ('무궁화',    _mugunghwa),
    'hanok':     ('한옥',      _hanok),
}
NEEDS_NG = {'chaekgado', 'saekdong', 'wanja', 'mugunghwa'}


def build(design, NG):
    name, fn = DESIGNS[design]
    out = fn(NG) if design in NEEDS_NG else fn()
    out['label'] = name
    return out


if __name__ == '__main__':
    for key in DESIGNS:
        d = build(key, 10)
        print(f"{key:<10} {d['label']:<7} 테두리 {len(d['frame']):3d}점 · "
              f"구역 {len(d['regions']) if d['regions'] else '자동':>4} · 장식 {len(d['decor']):3d}개")
