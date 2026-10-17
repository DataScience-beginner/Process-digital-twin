"""Fast, source-neutral, single-P&ID preliminary digitizer for *vector PDFs*.

No user/customer fixtures. One invocation makes a full-sheet source geometry markup,
a candidate plant graph and an audit report. Its CAD-stroke graph is GEOMETRIC
ONLY: no stroke is silently promoted to an engineering pipe edge.
"""
from __future__ import annotations
import hashlib, io, json, math, re, time, zipfile
from collections import Counter, defaultdict
from typing import Any

import fitz
from PIL import Image, ImageDraw

SCHEMA = 'pid-one-upload-candidate-graph-v1'
MAX_BYTES = 55*1024*1024
STROKE_MIN = 32.0
SNAP_TOLERANCE = 2.2


def _is_red(item):
    c=item.get('color')
    return bool(c and len(c)==3 and c[0]>.9 and c[1]<.1 and c[2]<.1)


def _rect_coords(rect):
    return [round(float(v),2) for v in (rect.x0,rect.y0,rect.x1,rect.y1)]


def _txt_in(rect,words):
    subset=[w for w in words if rect.x0+1<(w[0]+w[2])/2<rect.x1-1 and rect.y0+1<(w[1]+w[3])/2<rect.y1-1]
    return ' '.join(w[4] for w in sorted(subset,key=lambda x:(round(x[1]/8),x[0])))


def _geom_profiles(drawings,words):
    circles,quads,strokes=[],[],[]
    for idx,item in enumerate(drawings):
        if not _is_red(item): continue
        rr=item['rect'];types={g[0] for g in item['items']}
        if types=={'c'} and 29.5<=rr.width<=40 and 29.5<=rr.height<=40 and abs(rr.width-rr.height)<.5:
            circles.append((idx,rr))
        if types in ({'qu'},{'re'}) and 24<rr.width<45 and 24<rr.height<45:
            quads.append((idx,rr))
        for z in item['items']:
            if z[0]=='l':strokes.append((idx,z[1],z[2]))
    seen=set();out=[]
    for idx,rect in circles:
        key=tuple(round(x,1) for x in (rect.x0,rect.y0,rect.x1,rect.y1))
        if key in seen:continue
        seen.add(key)
        boxes=[j for j,r in quads if max(abs(r.x0-rect.x0),abs(r.y0-rect.y0),abs(r.x1-rect.x1),abs(r.y1-rect.y1))<=1.3]
        div=[j for j,a,b in strokes if abs(a.y-b.y)<1.1 and abs(a.y-(rect.y0+rect.y1)/2)<rect.height*.13
             and min(a.x,b.x)>=rect.x0-.6 and max(a.x,b.x)<=rect.x1+.6 and abs(a.x-b.x)>=rect.width*.63]
        profile=('SQUARE_CIRCLE_DIVIDER' if boxes and div else 'SQUARE_CIRCLE' if boxes else 'CIRCLE_DIVIDER' if div else 'PLAIN_CIRCLE')
        out.append({'id':f'INS-{len(out)+1:04d}','kind':'instrument_shape','geometry_profile':profile,
            'source_text':_txt_in(rect,words),'bbox_pdf_pt':_rect_coords(rect),
            'center_pdf_pt':[round((rect.x0+rect.x1)/2,2),round((rect.y0+rect.y1)/2,2)],
            'native_geometry_evidence':{'circle_path':idx,'enclosure_paths':boxes,'divider_paths':div},
            'legend_match_status':'GEOMETRY_ONLY_NEEDS_EXACT_CLIENT_LEGEND_CLASS',
            'review_status':'CANDIDATE','engineering_accepted':False})
    return out


def _cad_strokes(drawings,page):
    out=[];seen=set()
    for item in drawings:
        if not _is_red(item):continue
        for z in item['items']:
            if z[0]!='l':continue
            a,b=z[1],z[2]
            dx,dy=abs(a.x-b.x),abs(a.y-b.y)
            if max(dx,dy)<STROKE_MIN or min(dx,dy)>2.8:continue
            if not (0<=a.x<=page.rect.width and 0<=b.x<=page.rect.width and 0<=a.y<=page.rect.height and 0<=b.y<=page.rect.height):continue
            key=tuple(round(x,1) for x in (min(a.x,b.x),min(a.y,b.y),max(a.x,b.x),max(a.y,b.y)))
            if key in seen:continue
            seen.add(key)
            out.append({'id':f'SEG-{len(out)+1:04d}','a':[round(a.x,2),round(a.y,2)],
                'b':[round(b.x,2),round(b.y,2)],'kind':'CAD_STROKE_UNCLASSIFIED',
                'source_line_path_evidence_only':True,'process_pipe_accepted':False})
    return out


def _stroke_endpoint_network(segments,tol=SNAP_TOLERANCE):
    """Geometric endpoint-only components; crossing/interior tees never join."""
    points=[]
    for seg in segments: points.extend([seg['a'],seg['b']])
    parent=list(range(len(points)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(i,j):
        a,b=find(i),find(j)
        if a!=b:parent[b]=a
    cell=max(tol,0.1);bins=defaultdict(list)
    for i,p in enumerate(points):
        cx=int(p[0]//cell);cy=int(p[1]//cell)
        for gx in range(cx-1,cx+2):
            for gy in range(cy-1,cy+2):
                for j in bins[(gx,gy)]:
                    if math.dist(p,points[j])<=tol:union(i,j)
        bins[(cx,cy)].append(i)
    roots=defaultdict(list)
    for i in range(len(points)):roots[find(i)].append(i)
    labels={root:f'GEO-{n:04d}' for n,root in enumerate(sorted(roots),1)}
    memberships={}
    for root,indices in roots.items():
        for i in indices:memberships[i]=labels[root]
    adj=[]
    for s in range(len(segments)):
        adj.append({'cad_stroke_id':segments[s]['id'],'point_a_id':memberships[s*2],
                    'point_b_id':memberships[s*2+1],'review_status':'GEOMETRIC_ENDPOINT_ONLY'})
    return {'endpoint_clusters':len(roots),'candidate_cad_stroke_edges':adj,
            'explicitly_excludes':'interior tees, stroke crossings, flow direction and physical piping class'}


def _word_register(words):
    line=[];eq=[];other=[]
    for w in words:
        t=w[4].strip()
        box=[round(w[i],2) for i in range(4)]
        if ('-' in t and re.search(r'\b(?:OWS|P|LPG|A|S|N|PW|SW|CW)-\d{2,}',t,re.I)) or re.search(r'\d+\"-\w+-\d',t):
            line.append({'source_text':t,'bbox_pdf_pt':box,'association_status':'UNVERIFIED_LINE_TAG_PROXIMITY'})
        elif re.fullmatch(r'\d{2}-[A-Z]{1,4}-\d{3,5}(?:-[A-Z])?',t):
            eq.append({'source_text':t,'bbox_pdf_pt':box,'association_status':'TAG_TEXT_ONLY'})
        elif re.fullmatch(r'[A-Z]{1,5}[- ]?\d{3,5}',t):
            other.append({'source_text':t,'bbox_pdf_pt':box,'association_status':'TAG_TEXT_ONLY'})
    return {'line_tag_observations':line,'equipment_tag_observations':eq,'other_tag_observations':other}


def _import_reviewed(reviewed,pdf_sha,page_1based):
    if reviewed is None:return {'approved_local_equipment_nodes':[],'approved_local_ports':[],'owner_reviewed_visual_paths':[]}
    if reviewed.get('source_sha256')!=pdf_sha or int(reviewed.get('source_page_1based',-1))!=page_1based:
        raise ValueError('Supplied owner review does not match this source PDF SHA-256 and page')
    return {'approved_local_equipment_nodes':reviewed.get('approved_local_equipment_nodes',[]),
            'approved_local_ports':reviewed.get('approved_local_ports',[]),
            'owner_reviewed_visual_paths':reviewed.get('reviewed_visual_path_evidence',[])}


def _overlay(page,instruments,strokes,tags,reviewed,scale=.82):
    # Never cover source drawing: translucent geometry is unavailable in PIL; use thin outlines.
    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
    im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    d=ImageDraw.Draw(im)
    for s in strokes:
        a=tuple(int(x*scale) for x in s['a']);b=tuple(int(x*scale) for x in s['b'])
        d.line([a,b],fill='#79c2c8',width=1)
    colors={'SQUARE_CIRCLE_DIVIDER':'#d13e27','SQUARE_CIRCLE':'#d13e27','CIRCLE_DIVIDER':'#ba7e29','PLAIN_CIRCLE':'#257be5'}
    for x in instruments:
        bb=x['bbox_pdf_pt'];d.rectangle([int(z*scale) for z in bb],outline=colors[x['geometry_profile']],width=2)
    for t in tags['equipment_tag_observations']:
        d.rectangle([int(z*scale) for z in t['bbox_pdf_pt']],outline='#8f35ae',width=2)
    for node in reviewed['approved_local_equipment_nodes']:
        x,y=node['center'];r=20
        d.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale),outline='#168e39',width=4)
    for p in reviewed['approved_local_ports']:
        x,y=p['source_attachment_pdf_pt'];r=5
        d.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale),outline='#168e39',width=3)
    for r in reviewed['owner_reviewed_visual_paths']:
        pts=r.get('path_pdf_point_waypoints',[])
        if len(pts)>1:d.line([(int(x*scale),int(y*scale)) for x,y in pts],fill='#1eaa50',width=3)
    head='FAST SOURCE-BASED CANDIDATES | Red: compound symbol  Blue: circle  Cyan: CAD stroke  Green: owner visual evidence'
    d.rectangle((0,0,min(im.width-1,1500),25),fill='#fcfcfc')
    d.text((8,5),head,fill='#222222')
    bio=io.BytesIO();im.save(bio,'PNG',optimize=False)
    return bio.getvalue()


def _make_pdf_markup(pdf_bytes,page_1based,instruments,reviewed):
    # Source remains vector and zoomable. Only derived customer output; never public repository.
    with fitz.open(stream=pdf_bytes,filetype='pdf') as original:
        one=fitz.open()
        one.insert_pdf(original,from_page=page_1based-1,to_page=page_1based-1)
        pg=one[0]
        for record in instruments:
            rect=fitz.Rect(record['bbox_pdf_pt'])
            is_composite=record['geometry_profile'] in ('SQUARE_CIRCLE_DIVIDER','SQUARE_CIRCLE')
            pg.draw_rect(rect,color=(.88,.1,.08) if is_composite else (.1,.42,.84),width=1.7,overlay=True)
        for n in reviewed['approved_local_equipment_nodes']:
            x,y=n['center'];pg.draw_circle((x,y),20,color=(0,.65,.25),width=3,overlay=True)
        for p in reviewed['approved_local_ports']:
            x,y=p['source_attachment_pdf_pt'];pg.draw_circle((x,y),6,color=(0,.65,.25),width=2,overlay=True)
        for r in reviewed['owner_reviewed_visual_paths']:
            points=r.get('path_pdf_point_waypoints',[])
            for a,b in zip(points,points[1:]):pg.draw_line(a,b,color=(0,.68,.25),width=2.5,overlay=True)
        bio=one.tobytes(garbage=3,deflate=True)
        one.close()
        return bio

def process_single_page(pdf_bytes,page_1based=1,*,approved_review=None,render_scale=.82):
    """The measured processing unit used by both CLI and HTTP. No uploads/network here."""
    t0=time.perf_counter()
    if not pdf_bytes or len(pdf_bytes)>MAX_BYTES:raise ValueError('PDF empty or over 55MiB per-upload limit')
    if pdf_bytes[:4]!=b'%PDF':raise ValueError('Only source PDF files supported')
    sha=hashlib.sha256(pdf_bytes).hexdigest()
    with fitz.open(stream=pdf_bytes,filetype='pdf') as doc:
        if page_1based<1 or page_1based>len(doc):raise ValueError('page number out of range')
        page=doc[page_1based-1]
        drawings=page.get_drawings();words=page.get_text('words')
        if len(drawings)<2:raise ValueError('Raster/unsupported PDF drawing: route to a separate raster model, do not claim complete recognition')
        instruments=_geom_profiles(drawings,words)
        strokes=_cad_strokes(drawings,page)
        tags=_word_register(words)
        reviewed=_import_reviewed(approved_review,sha,page_1based)
        network=_stroke_endpoint_network(strokes)
        t_extract=time.perf_counter()
        overlay=_overlay(page,instruments,strokes,tags,reviewed,scale=render_scale)
        pdf_preview=_make_pdf_markup(pdf_bytes,page_1based,instruments,reviewed)
    t_done=time.perf_counter()
    summary={'native_vector_paths':len(drawings),'instrument_geometry_count':len(instruments),
        'instrument_geometry_profiles':dict(Counter(x['geometry_profile'] for x in instruments)),
        'raw_cad_stroke_count':len(strokes),'geometric_endpoint_clusters':network['endpoint_clusters'],
        'line_tag_text_count':len(tags['line_tag_observations']),
        'equipment_tag_text_count':len(tags['equipment_tag_observations']),
        'approved_equipment_locations':len(reviewed['approved_local_equipment_nodes']),
        'approved_local_ports':len(reviewed['approved_local_ports']),
        'reviewed_visual_paths':len(reviewed['owner_reviewed_visual_paths']),
        'accepted_physical_graph_edges':0,
        'unknown_symbol_class_count':len(instruments),
        'page_candidate_complete':False}
    graph={'schema':SCHEMA,'source_sha256':sha,'page_1based':page_1based,'page_type':'VECTOR_PDF',
        'coordinate_space':'displayed_pdf_points','nodes':{'instrument_shape_candidates':instruments,
        'source_text':tags,'owner_reviewed_local_equipment':reviewed['approved_local_equipment_nodes'],
        'owner_reviewed_local_ports':reviewed['approved_local_ports']},
        'edges':{'source_cad_strokes':strokes,'geometric_endpoint_network':network,
        'owner_reviewed_visual_paths_NOT_physical_pipe_edges':reviewed['owner_reviewed_visual_paths'],
        'engineering_approved_physical_connections':[]},
        'provisional_graph_only':True,'publish_ready':False,
        'limits':['Only red CAD geometry is considered in this fast pilot',
        'No full symbol classification accuracy established',
        'DCS classes are geometry-family proposals, not complete legend semantic approvals',
        'Long CAD strokes may include annotations/signal lines and are not process pipes',
        'Endpoint clusters are geometric only, crossing/tees and directions unverified',
        'Pump/route owner-reviewed evidence, when supplied, is not a physical network approval']}
    perf={'extraction_seconds':round(t_extract-t0,3),'render_seconds':round(t_done-t_extract,3),
        'whole_drawing_seconds':round(t_done-t0,3),'target_seconds':60,'below_60s_local_processing':t_done-t0<60,
        'scope':'local source page ingest -> candidate geometry -> source stroke graph -> rendered preview; excludes internet transfer, external services and user approval'}
    return {'graph':graph,'summary':summary,'benchmark':perf,'overlay_png':overlay,'annotated_pdf':pdf_preview}


def make_zip(payload):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=4) as z:
        z.writestr('whole_sheet_markup.png',payload['overlay_png'])
        z.writestr('whole_sheet_annotated_vector.pdf',payload['annotated_pdf'])
        z.writestr('candidate_graph.json',json.dumps(payload['graph'],indent=2))
        z.writestr('candidate_counts_and_benchmark.json',json.dumps({'summary':payload['summary'],'benchmark':payload['benchmark']},indent=2))
        z.writestr('READ_ME_FIRST.txt','Preliminary vector-PDF digitization only. CAD strokes and geometrical endpoint clusters are not verified process pipe connections. Exact DCS semantics and any unknown equipment require review. No physical graph edges approved.\n')
    return out.getvalue()
