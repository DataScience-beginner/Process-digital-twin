"""Source-neutral one-pass vector P&ID candidate extractor.

Batch-extract bubbles and long native-CAD stroke observations from ONE P&ID.
Candidates have no certified class or physical connectivity; a source review
is required before graph-edge publication. No customer fixtures are bundled.
"""
from __future__ import annotations
import hashlib
import math
from typing import Any
import fitz


def extract_native_candidates(pdf_bytes: bytes, page_1based: int,
                              *, x_limit: float | None = None,
                              y_limit: float | None = None) -> dict[str, Any]:
    if not pdf_bytes:
        raise ValueError('Provide original source PDF bytes')
    with fitz.open(stream=pdf_bytes, filetype='pdf') as doc:
        if page_1based < 1 or page_1based > len(doc):
            raise ValueError('PDF page out of range')
        pg = doc[page_1based-1]
        x_max = x_limit if x_limit is not None else pg.rect.width
        y_max = y_limit if y_limit is not None else pg.rect.height
        words = pg.get_text('words')
        circles, strokes = [], []
        seen_circle, seen_stroke = set(),set()
        for item in pg.get_drawings():
            if item['color'] != (1.0, 0.0, 0.0):
                continue
            r = item['rect']
            if (30 < r.width < 39 and 30 < r.height < 39 and
                abs(r.width-r.height) < 0.5 and r.x0 < x_max and r.y0 < y_max and
                any(z[0] == 'c' for z in item['items'])):
                cc=((r.x0+r.x1)/2,(r.y0+r.y1)/2)
                key=(round(cc[0],1),round(cc[1],1))
                if key not in seen_circle:
                    seen_circle.add(key)
                    txt=' '.join(w[4] for w in sorted(words,key=lambda w:(w[1],w[0]))
                        if r.x0-1 < (w[0]+w[2])/2 < r.x1+1 and
                           r.y0-1 < (w[1]+w[3])/2 < r.y1+1)
                    if txt and not txt.startswith('3/4x1'):
                        circles.append({'id':f'BUBBLE-{len(circles)+1:04d}',
                           'source_text':txt,'bbox_pdf_pt':[round(v,2) for v in (r.x0,r.y0,r.x1,r.y1)],
                           'status':'UNREVIEWED_CANDIDATE'})
            for geom in item['items']:
                if geom[0] != 'l':
                    continue
                a,b=geom[1],geom[2]
                dx,dy=abs(a.x-b.x),abs(a.y-b.y)
                if (max(dx,dy)<32 or min(dx,dy)>2.8 or
                    not (0<a.x<x_max and 0<b.x<x_max and 0<a.y<y_max and 0<b.y<y_max)):
                    continue
                key=(round(min(a.x,b.x),1),round(min(a.y,b.y),1),
                     round(max(a.x,b.x),1),round(max(a.y,b.y),1))
                if key in seen_stroke:
                    continue
                seen_stroke.add(key)
                strokes.append({'id':f'CAD-STROKE-{len(strokes)+1:04d}',
                    'start_pdf_pt':[round(a.x,2),round(a.y,2)],
                    'end_pdf_pt':[round(b.x,2),round(b.y,2)],
                    'classification':'UNREVIEWED_NATIVE_CAD_STROKE',
                    'process_piping_confirmed':False})
    return {'schema':'pid-native-onepass-v1','source_sha256':hashlib.sha256(pdf_bytes).hexdigest(),
        'source_page_1based':page_1based,'instrument_bubble_candidates':circles,
        'source_cad_stroke_candidates':strokes,
        'approved_physical_graph_edges':[],
        'engineering_publish_ready':False}
