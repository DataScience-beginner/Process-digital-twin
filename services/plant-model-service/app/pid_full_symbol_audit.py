"""Native-vector, source-neutral P&ID motif scanner (preliminary geometry candidates).

Returns whole symbol envelopes rather than merely circle primitives. Exact class,
normal position, physical connectivity and drawing coverage require review.
No customer source, tags or labels are embedded in this module.
"""
from __future__ import annotations
from collections import Counter
import math


def _red(path):
    c = path.get('color')
    return bool(c and len(c) == 3 and c[0] > .9 and c[1] < .1 and c[2] < .1)


def _center(rect):
    return ((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


def _box(rect):
    return [round(rect.x0, 2), round(rect.y0, 2), round(rect.x1, 2), round(rect.y1, 2)]


def _is_axis_aligned_quad(path):
    if any(cmd[0] == 're' for cmd in path.get('items', [])):
        return True
    for cmd in path.get('items', []):
        if cmd[0] == 'qu':
            q = cmd[1]
            return abs(q.ul.x - q.ur.x) < 1 or abs(q.ul.y - q.ur.y) < 1
    return False


def _word_text(rect, words):
    x0, y0, x1, y1 = rect
    return ' '.join(w[4] for w in sorted(words, key=lambda w: (w[1] // 10, w[0]))
                    if x0 - 1 < (w[0] + w[2]) / 2 < x1 + 1
                    and y0 - 1 < (w[1] + w[3]) / 2 < y1 + 1)[:140]


def scan_native_motifs(page, drawings=None, words=None):
    """Extract CAD source motif proposals across a vector page.

    The count is NOT a detector recall. A motif may be an annotation, a device,
    or only a fragment. All returned items default to UNREVIEWED.
    """
    drawings = drawings if drawings is not None else page.get_drawings()
    words = words if words is not None else page.get_text('words')
    valid = lambda r: r.x0 > 3 and r.y0 > 3 and r.x1 < page.rect.width - 3 and r.y1 < page.rect.height - 3
    circles, quads, triangles, bows, strokes, small = [], [], [], [], [], []
    for idx, path in enumerate(drawings):
        if not _red(path):
            continue
        r = path['rect']; ops = path['items']; kinds = {x[0] for x in ops}
        if kinds == {'c'} and abs(r.width - r.height) < .8:
            if 29 < r.width < 43: circles.append((idx, r))
            elif 2.8 < r.width < 9: small.append((idx, r))
        if ('qu' in kinds or 're' in kinds) and 26 < r.width < 46 and 26 < r.height < 46:
            quads.append((idx, r))
        for entry in ops:
            if entry[0] == 'l': strokes.append((idx, entry[1], entry[2], path['type']))
        if kinds == {'l'} and len(ops) == 3 and 2.5 < r.width < 45 and 2.5 < r.height < 45:
            points = {(round(v.x, 1), round(v.y, 1)) for segment in ops for v in segment[1:3]}
            if len(points) == 4 and 8 < r.width < 20 and 7 < r.height < 20:
                if max(r.width / r.height, r.height / r.width) < 2.4:
                    bows.append((idx, r, path['type']))
            if len(points) == 3:
                triangles.append((idx, r, path['type']))
    out, counts = [], Counter()

    def add(family, rect, path_ids, subtype, reference=None):
        counts[family] += 1
        out.append({'id': f'{family}-{counts[family]:03d}', 'family': family,
                    'bbox_pdf_pt': _box(rect), 'drawing_path_ids': sorted(set(path_ids)),
                    'source_text_inside': _word_text(_box(rect), words),
                    'subtype_geometry': subtype, 'suggested_legend_id_not_verified': reference,
                    'review_status': 'UNREVIEWED', 'physical_pipe_edge_approved': False})

    seen = set()
    for idx, rect in circles:
        key = tuple(round(q, 1) for q in _box(rect))
        if key in seen or not valid(rect): continue
        seen.add(key)
        boxes = [(j, q) for j, q in quads if _is_axis_aligned_quad(drawings[j])
                 and math.dist(_center(q), _center(rect)) < 2.5]
        div = [j for j, a, b, _ in strokes if abs(a.y-b.y) < .7
               and abs(a.y-_center(rect)[1]) < 5 and abs(a.x-b.x) > rect.width*.64
               and min(a.x,b.x) >= rect.x0-3 and max(a.x,b.x) <= rect.x1+3]
        bb = rect
        for _, square in boxes: bb = bb | square
        if boxes and div: subtype, reference = 'CIRCLE_SQUARE_DIVIDER', 'DB_P40_023'
        elif boxes: subtype, reference = 'CIRCLE_SQUARE', 'DB_P40_024'
        elif div: subtype, reference = 'CIRCLE_DIVIDER', 'DB_P40_034'
        else: subtype, reference = 'FIELD_CIRCLE', 'DB_P40_031'
        add('INSTRUMENT_ENVELOPE', bb, [idx]+[j for j, _ in boxes]+div, subtype, reference)
    for idx, rect in quads:
        if not valid(rect): continue
        if any(math.dist(_center(rect), _center(q)) < 2.5 for _, q in circles): continue
        diamond = not _is_axis_aligned_quad(drawings[idx])
        subtype = 'ROTATED_DIAMOND_INTERLOCK_OR_ALARM' if diamond else 'SQUARE_FUNCTION_BLOCK'
        add('INTERLOCK_LOGIC', rect, [idx], subtype, 'DB_P40_029' if diamond else None)
    for idx, rect, _ in bows:
        if not valid(rect): continue
        if any(rect.x0 >= r.x0 and rect.x1 <= r.x1 and rect.y0 >= r.y0 and rect.y1 <= r.y1 for _, r in circles):continue
        add('INLINE_VALVE_FAMILY', rect, [idx], 'BOWTIE_UNSPECIFIED', 'SHEET39_COL_C_001')
    filled = [(i,r) for i,r,t in triangles if t=='fs' and 7 < r.width < 12 and 6 < r.height < 9]
    for n,(idx,r) in enumerate(filled):
        if not valid(r):continue
        for j,q in filled[n+1:]:
            if abs(q.x0-r.x0)<1.2 and abs(q.x1-r.x1)<1.2 and abs(q.y0-r.y1)<1:
                if not any((r | q).intersects(b) and (r | q).get_area()>1
                           and ((r | q)&b).get_area() / (r | q).get_area() > .6 for _,b,_ in bows):
                    add('INLINE_VALVE_FAMILY',r | q,[idx,j],'FILLED_BOWTIE_UNSPECIFIED')
    for idx,r,_ in triangles:
        if valid(r) and 15 < r.width < 19 and 13 < r.height < 17:
            add('NOTE_MARKER_NOT_EQUIPMENT',r,[idx],'TRIANGLE_NUMBER_REFERENCE')
    for idx,r,kind in triangles:
        if not valid(r) or kind!='fs' or not(3.8<r.width<35 and 3.8<r.height<15):continue
        if any((r&b).get_area()/max(1,r.get_area())>.45 for _,b,_ in bows):continue
        add('FILLED_ARROW_CANDIDATE',r,[idx],'ARROW_SHUTTER_OR_MOTIF_UNVERIFIED')
    dedup=set()
    for idx,r in small:
        if not valid(r):continue
        key=(int(_center(r)[0]//2),int(_center(r)[1]//2))
        if key in dedup:continue
        dedup.add(key)
        add('SMALL_ROUND_CAD_MOTIF',r,[idx],'SMALL_LOOP_NOZZLE_OR_JOIN_UNSPECIFIED')
    return {'candidates': out, 'counts': dict(counts), 'source_page_1based': page.number+1,
            'source_paths_inspected': len(drawings), 'symbol_detection_recall_measured': False,
            'engineering_graph_edges_accepted': 0}
