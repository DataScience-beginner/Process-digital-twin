"""Conservative source-vector graph *proposals* for P&ID drawings.

Entire glyphs, source strokes and native words are observed in one pass.
No geometric relationship is an engineering-approved pipe edge. Crossings and
tees remain unresolved; text proximity never assigns a piping line number.
This module contains no customer drawing data, legends, images or templates.
"""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
import math
import re

_LINE_TAG = re.compile(r'(?:\d+(?:/\d+)?(?:\(H\))?"-)?(?:P|OWS|HO|CW|SW|PW)-\d{2}-\d{4}', re.I)


def _red(path):
    c=path.get('color')
    return bool(c and len(c)==3 and c[0]>.9 and c[1]<.1 and c[2]<.1)


def _grid(x,y,side):
    return int(x//side),int(y//side)


def build_candidate_relationships(drawings, words, symbols, *, drawing_bbox=None,
                                  snap_tolerance=2.0, min_stroke_length=8.0,
                                  port_distance=6.0):
    """Return source-evidenced, UNAPPROVED symbol/stroke/line relationships.

    Args:
      drawings: native PyMuPDF ``page.get_drawings()`` records.
      words: native PyMuPDF ``page.get_text('words')`` records.
      symbols: sequence of dicts with ``id``, ``bbox_pdf_pt``, optional ``family``.
      drawing_bbox: optional PDF-points content region excluding a source titleblock.

    Never connects an endpoint-to-interior tee or two crossing interiors.
    Does not distinguish process from signal/annotation solely on CAD color.
    """
    if snap_tolerance<=0 or min_stroke_length<=0:raise ValueError('Invalid tolerances')
    strokes=[]
    bounds=drawing_bbox
    for path_i,d in enumerate(drawings):
        if not _red(d):continue
        for item_i,z in enumerate(d.get('items',[])):
            if z[0]!='l':continue
            a,b=z[1:3];dx=abs(a.x-b.x);dy=abs(a.y-b.y)
            if math.hypot(dx,dy)<min_stroke_length or min(dx,dy)>1.2:continue
            if bounds and not all(bounds[0]<x<bounds[2] and bounds[1]<y<bounds[3] for x,y in ((a.x,a.y),(b.x,b.y))):continue
            strokes.append({'id':f'CAD-{len(strokes)+1:05d}', 'source_path_id':path_i,
               'source_item_id':item_i,'a':[round(a.x,2),round(a.y,2)],
               'b':[round(b.x,2),round(b.y,2)],'axis':'H' if dx>=dy else 'V',
               'cad_role':'UNCLASSIFIED','physical_pipe_accepted':False})
    # Spatial union/find on real source stroke endpoints only.
    pts=[tuple(s[k]) for s in strokes for k in ('a','b')]
    parents=list(range(len(pts)))
    def find(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parents[b]=a
    bins=defaultdict(list);cell=snap_tolerance
    for i,(x,y) in enumerate(pts):
        gx,gy=_grid(x,y,cell)
        for jx in range(gx-1,gx+2):
            for jy in range(gy-1,gy+2):
                for j in bins[(jx,jy)]:
                    if math.dist(pts[j],(x,y))<=snap_tolerance:union(i,j)
        bins[(gx,gy)].append(i)
    for i in range(len(strokes)):union(2*i,2*i+1)
    roots={};runs=defaultdict(list)
    for i,s in enumerate(strokes):
        rt=find(2*i)
        if rt not in roots:roots[rt]=f'RUN-{len(roots)+1:04}'
        s['run_id']=roots[rt];runs[s['run_id']].append(s['id'])
    # Exactly source-based per-symbol side-port candidates. Only nearest observed
    # stroke ENDPOINTS qualify; this prevents silent endpoint-on-interior joins.
    attachments=[];by_run=defaultdict(set)
    point_bins=bins  # indices keyed on endpoints before union
    for s in symbols:
        bb=s['bbox_pdf_pt'];x0,y0,x1,y1=bb
        ports=[('W',(x0,(y0+y1)/2)),('E',(x1,(y0+y1)/2)),
               ('N',((x0+x1)/2,y0)),('S',((x0+x1)/2,y1))]
        for side,p in ports:
            gx,gy=_grid(*p,cell);neighbors=[]
            span=int(math.ceil(port_distance/cell))+1
            for xx in range(gx-span,gx+span+1):
                for yy in range(gy-span,gy+span+1):
                    for idx in point_bins.get((xx,yy),[]):
                        dist=math.dist(p,pts[idx])
                        if dist<=port_distance:neighbors.append((dist,idx))
            if not neighbors:continue
            distance,ind=min(neighbors)
            stroke=strokes[ind//2]
            att={'id':f'ATT-{len(attachments)+1:05}', 'symbol_id':s['id'], 'symbol_side':side,
                'source_stroke_id':stroke['id'],'candidate_run_id':stroke['run_id'],
                'distance_pt':round(distance,2),'status':'GEOMETRY_PROPOSAL'}
            attachments.append(att);by_run[stroke['run_id']].add(s['id'])
    relations=[]
    for run_id,symids in by_run.items():
        for left,right in combinations(sorted(symids),2):
            relations.append({'id':f'REL-{len(relations)+1:04}','from_symbol_id':left,
                  'to_symbol_id':right,'shared_CAD_run_id':run_id,
                  'evidence_stroke_ids':runs[run_id],
                  'status':'CANDIDATE_SHARED_STROKE_NOT_PHYSICAL_PIPE',
                  'engineering_accepted':False})
    # tee / crossing detector using page-local spatial H/V intersection checks.
    vertical=defaultdict(list);horizontal=[]
    bucket_size=24
    for s in strokes:
        a,b=s['a'],s['b']
        if s['axis']=='H':horizontal.append(s)
        else:
            x=a[0];ylo,yhi=sorted((a[1],b[1]))
            for cell_y in range(int(ylo//bucket_size),int(yhi//bucket_size)+1):
                vertical[(int(x//bucket_size),cell_y)].append(s)
    tees=[];crosses=[];seen=set()
    for a in horizontal:
        y=a['a'][1];xx0,xx1=sorted((a['a'][0],a['b'][0]))
        candidates=[]
        for x_cell in range(int(xx0//bucket_size),int(xx1//bucket_size)+1):
            candidates+=vertical.get((x_cell,int(y//bucket_size)),[])
        for b in candidates:
            x=b['a'][0];yy0,yy1=sorted((b['a'][1],b['b'][1]))
            if not(xx0-1<=x<=xx1+1 and yy0-1<=y<=yy1+1):continue
            near_a=abs(x-a['a'][0])<1.7 or abs(x-a['b'][0])<1.7
            near_b=abs(y-b['a'][1])<1.7 or abs(y-b['b'][1])<1.7
            if near_a and near_b:continue
            kind='ENDPOINT_TO_INTERIOR_T_CANDIDATE' if near_a!=near_b else 'INTERIOR_INTERIOR_CROSSING'
            unique=(round(x,1),round(y,1),kind)
            if unique in seen:continue
            seen.add(unique)
            # glyph interiors commonly contain axis lines, never call those physical tees
            if any(sy['bbox_pdf_pt'][0]-2<x<sy['bbox_pdf_pt'][2]+2 and sy['bbox_pdf_pt'][1]-2<y<sy['bbox_pdf_pt'][3]+2 for sy in symbols):continue
            record={'id':f'J-{len(tees)+len(crosses)+1:04}','pdf_pt':[round(x,2),round(y,2)],
              'source_stroke_ids':[a['id'],b['id']], 'geometry':kind,
              'connected':None,'status':'REQUIRES_REVIEW'}
            (tees if near_a!=near_b else crosses).append(record)
    # Never attach line IDs automatically, retain native text and nearby evidence.
    tags=[]
    for w in words:
        if not _LINE_TAG.search(w[4]):continue
        tags.append({'id':f'LINE-TEXT-{len(tags)+1:03}', 'verbatim':w[4],
          'bbox_pdf_pt':[round(z,2) for z in w[:4]],'pipe_association':'UNVERIFIED'})
    return {'cad_strokes':strokes,'cad_runs':runs,
      'symbol_cad_attachments':attachments,'shared_run_symbol_relationships':relations,
      'tee_candidates':tees,'unresolved_interior_crossings':crosses,
      'native_line_tags_unassigned':tags,
      'statistics':{'stroke_count':len(strokes),'run_count':len(runs),'attachment_candidates':len(attachments),
        'shared_run_relations':len(relations),'tee_candidates':len(tees),'crossing_candidates':len(crosses),
        'line_tag_occurrences':len(tags)},
      'safety':{'all_relationships_engineering_accepted':False,
          'physical_graph_edges_approved':0,
          'explanation':'Geometry-only; CAD may be annotation, signal or pipe. Tees/crossings and line-tag associations require explicit review.'}}
