"""Generic, conservative vector P&ID review helpers.

No project/vendor data; source-derived outputs are created in a private workspace.
Component text and line primitives are observations, not a reviewed graph.
"""
from __future__ import annotations
import math, re, hashlib
from collections import Counter
from typing import Any
import fitz

EQUIP_RX=re.compile(r"\b\d{2}-(?:PA|TT|PK|VV)-\d{3}\s*[A-C]?(?:\s*/\s*[A-C]){0,2}\b",re.I)
INST_CODES=frozenset({'LT','LI','TT','TI','PT','PI','PG','FT','FIC','FE','TE','TSV','ROSOV','HS','XL','LM','LIT','XV','FI','PIC','LIC','TC','FQ','FQI'})

def source_sha256(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def extract_source_spans(page:fitz.Page)->list[dict]:
    spans=[]
    for b in page.get_text('dict')['blocks']:
        for line in b.get('lines',[]):
            for s in line['spans']:
                txt=s['text'].strip()
                if txt:
                    spans.append({'text':txt,'bbox':[round(z,2) for z in s['bbox']],
                                  'size':round(s['size'],2)})
    return spans

def _center(r):return ((r[0]+r[2])/2,(r[1]+r[3])/2)

def _dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])

def extract_tags(page:fitz.Page)->list[dict]:
    spans=extract_source_spans(page)
    res=[];seen=set()
    for k,s in enumerate(spans):
        text=s['text'].strip()
        box=s['bbox'];cx,cy=_center(box)
        if cx>page.rect.width*.84 or cy>page.rect.height*.94: continue # document notes / title region
        equipment=EQUIP_RX.search(text)
        if equipment:
            tag=' '.join(equipment.group(0).upper().split())
            key=('equipment',tag,round(cx,1),round(cy,1))
            if key not in seen:
                seen.add(key)
                res.append({'type':'equipment_text','tag_text':tag,'bbox_pdf_pt':box,
                    'id':f'TXT-EQ-{len(res)+1:04d}','review_status':'unreviewed',
                    'note':'Text occurrence; candidate association to physical glyph is unverified'})
            continue
        t=re.sub(r'[^A-Z]','',text.upper())
        if t not in INST_CODES: continue
        if cy<page.rect.height*.035:continue
        # find a nearby loop number. Don't assert actual bubble / location.
        neighbors=[]
        for j,o in enumerate(spans):
            if j==k:continue
            num=o['text'].strip()
            if not re.fullmatch(r'\d{3,5}[A-C]?',num): continue
            c2=_center(o['bbox']);d=_dist((cx,cy),c2)
            if d<36:neighbors.append((d,num,j))
        nearest=min(neighbors,default=None)
        identity=(text+' '+nearest[1] if nearest else text).upper()
        key=('instrument',identity,round(cx/5),round(cy/5))
        if key in seen:continue
        seen.add(key)
        res.append({'type':'instrument_text','tag_text':identity,
                    'bbox_pdf_pt':box,'id':f'TXT-INS-{len(res)+1:04d}',
                    'review_status':'unreviewed',
                    'loop_code_assignment':'proposed_by_text_proximity' if nearest else 'not_found',
                    'note':'Text plus nearest loop code only, NOT a validated symbol'})
    return res

def extract_line_strokes(page:fitz.Page, min_len=30.0)->list[dict]:
    strokes=[]
    for draw in page.get_drawings():
        col=draw.get('color')
        if col is None or len(col)!=3 or not (col[0]>.8 and col[1]<.25 and col[2]<.25):continue
        for it in draw.get('items',[]):
            if it[0]!='l':continue
            a,b=it[1],it[2]
            if not (25<a.x<page.rect.width*.83 and 30<b.x<page.rect.width*.83 and
                     40<a.y<page.rect.height*.95 and 40<b.y<page.rect.height*.95):continue
            length=math.hypot(a.x-b.x,a.y-b.y)
            if length<min_len:continue
            axis='H' if abs(a.y-b.y)<1.8 else 'V' if abs(a.x-b.x)<1.8 else 'diagonal'
            if axis=='diagonal':continue
            strokes.append({'id':f'VEC-{len(strokes)+1:05d}','axis':axis,
              'start_pdf_pt':[round(a.x,2),round(a.y,2)],'end_pdf_pt':[round(b.x,2),round(b.y,2)],
              'length_pdf_pt':round(length,2),'status':'unreviewed_stroke',
              'connection_claim':False})
    return strokes

def build_draft_graph(tags:list[dict],source_hash:str, source_page:int)->dict[str,Any]:
    # Observations are NOT accepted nodes; no physical connectivity is fabricated.
    return {'schema':'pid-reviewed-graph-draft-v0.1','source_sha256':source_hash,
      'source_pdf_page_1based':source_page,'readiness':'NOT_READY',
      'observed_label_candidates':[{'id':c['id'],'tag_text':c['tag_text'],'bbox_pdf_pt':c['bbox_pdf_pt'],
       'kind_hint':c['type'],'status':'NOT_ACCEPTED'} for c in tags],
      'approved_nodes':[],'approved_edges':[],'unresolved_connections':[],
      'rules':['No line crossing automatically connected','No geometric PDF length treated as pipe length',
               'Equipment name proximity does not confirm symbol geometry','No hydraulics/MTO from unreviewed graph']}
