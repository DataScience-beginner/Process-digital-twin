"""Generic, PRIVATE legend review atlas builder for source-backed, human-reviewed examples.

This module contains no client images or catalog contents. Produced outputs are
restricted engineering source derivatives and MUST NOT be committed to public repos.

Input: JSON containing {"source_sha256", "pages": [int], "registry": [
    {"id": "SAMPLE", "pdf_page": 1, "image_bbox_pdf_pt": [x0,y0,x1,y1],
     "label_bbox_pdf_pt": [x0,y0,x1,y1] or null, "label_candidate": "...",
     "owner_mapping_approved": false}]}.
The manifest author must visually inspect the original sheet and propose bounds.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
from html import escape
import json
from pathlib import Path
from typing import Any
import fitz


def validate_registry(raw: bytes, registry: dict[str,Any]) -> list[dict]:
    digest = hashlib.sha256(raw).hexdigest()
    if registry.get("source_sha256") != digest:
        raise ValueError("Source fingerprint does not match manifest")
    pages = registry.get("pages")
    items = registry.get("registry")
    if not isinstance(pages,list) or not pages or not isinstance(items,list):
        raise ValueError("pages and registry entries required")
    out=[]; seen=set()
    with fitz.open(stream=raw,filetype="pdf") as pdf:
        for n in pages:
            if not isinstance(n,int) or isinstance(n,bool) or not 1<=n<=len(pdf) or n in seen:
                raise ValueError(f"Invalid or duplicated PDF page: {n}")
            seen.add(n)
        symbols=set()
        for item in items:
            n = item.get("pdf_page");key = item.get("id")
            if n not in seen or not isinstance(key,str) or not key or key in symbols:
                raise ValueError("Duplicate or unregistered source item")
            symbols.add(key)
            pg = pdf[n-1]
            boxes=[item.get("image_bbox_pdf_pt"),item.get("label_bbox_pdf_pt")]
            for b in boxes:
                if b is None:continue
                if not isinstance(b,list) or len(b)!=4 or any(isinstance(x,bool) or not isinstance(x,(int,float)) for x in b):
                    raise ValueError("Four numeric PDF-coordinate bounds required")
                x0,y0,x1,y1 = b
                if not (0<=x0<x1<=pg.rect.width and 0<=y0<y1<=pg.rect.height):
                    raise ValueError("Source bounds are outside the PDF page")
            if boxes[0] is None:
                raise ValueError("Graphical source region is required")
            if item.get("owner_mapping_approved") and not item.get("label_candidate"):
                raise ValueError("Approved glyph mapping must retain its source description")
            out.append(item)
    return out


def build_atlas(raw: bytes, registry: dict, output: Path, *, render_width: int=1400) -> dict:
    """Generate a fully offline visual inspection atlas; do not auto-approve entries."""
    items=validate_registry(raw, registry)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    rows=[]; full=[]
    with fitz.open(stream=raw,filetype="pdf") as pdf:
        for n in registry['pages']:
            pg=pdf[n-1]
            scale=render_width/pg.rect.width
            pix=pg.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
            src='data:image/png;base64,'+base64.b64encode(pix.tobytes('png')).decode('ascii')
            full.append({'page':n,'src':src})
        for row in items:
            pg=pdf[row['pdf_page']-1]
            get=lambda box:'data:image/png;base64,'+base64.b64encode(
                pg.get_pixmap(matrix=fitz.Matrix(2.5,2.5),clip=fitz.Rect(box),alpha=False).tobytes('png')
            ).decode('ascii') if box else ''
            rows.append({k:row.get(k) for k in ['id','pdf_page','label_candidate','owner_mapping_approved','kind','warning']}
                        | {'glyph':get(row['image_bbox_pdf_pt']),'label':get(row.get('label_bbox_pdf_pt'))})
    data=json.dumps({'pages':full,'items':rows,'source_sha256':registry['source_sha256']},ensure_ascii=False).replace('<','\\u003c')
    html='''<!DOCTYPE html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Engineering Legend Source Review</title><style>body{font:14px system-ui;color:#102539;background:#eef2f5;margin:0}header{position:sticky;top:0;background:#fff;padding:12px;z-index:2}main{display:grid;grid-template-columns:44% 55%;gap:1%;padding:16px}article{display:grid;grid-template-columns:44% 55%;gap:1%;border:1px solid #ccd;background:#fff;margin-bottom:8px;padding:9px}img{max-width:100%;max-height:220px;object-fit:contain}#sheet{width:100%;max-height:83vh;object-fit:contain;position:sticky;top:110px}button{background:#17647b;color:white;border:0;border-radius:5px;padding:9px;cursor:pointer}textarea{width:100%;box-sizing:border-box}small{color:#735000}body>header p{margin:4px 0}select{padding:6px}@media(max-width:800px){main,article{display:block}#sheet{position:static}}</style>
    <header><b>Engineering legend: entire source-page review</b><p>Original source image and candidate graphics. Previously approved only where explicit evidence exists. No bulk approval.</p>
    <select id="p" onchange="render()"></select><button onclick="exportDecisions()">Export my decisions</button><b id="stats"></b></header>
    <main><section><img id="sheet"></section><section id="results"></section></main>
    <script>const data=__STATE__;const q=document.getElementById('p');data.pages.forEach(x=>q.add(new Option('PDF page '+x.page,x.page)));q.value=data.pages[0].page;
    const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
    function render(){let n=Number(q.value),p=data.pages.find(x=>x.page===n);document.getElementById('sheet').src=p.src;
    document.getElementById('results').innerHTML=data.items.filter(x=>x.pdf_page===n).map(x=>`<article><div><b>${esc(x.id)}</b><br><small>${esc(x.kind)} | ${x.owner_mapping_approved?'Previously owner-approved':'Needs review'} | ${esc(x.warning)}</small><hr><img src="${x.glyph}">${x.label?`<p>Original adjacent label</p><img src="${x.label}">`:''}</div><div><label>Label / context<textarea data-id="${esc(x.id)}" data-field="label_candidate" rows=3 ${x.owner_mapping_approved?'readonly':''}>${esc(x.label_candidate)}</textarea></label><label>Review choice<select data-id="${esc(x.id)}" data-field="decision" ${x.owner_mapping_approved?'disabled':''}><option value="">Review needed</option><option value="approve">Approve</option><option value="correct">Correct bounds/label</option><option value="reject">Reject non-symbol</option></select></label><label>Notes<textarea data-id="${esc(x.id)}" data-field="notes" rows=2></textarea></label></div></article>`).join('');document.getElementById('stats').textContent=` ${data.items.length} review proposals; ${data.items.filter(x=>x.owner_mapping_approved).length} previous owner approvals`}
    document.getElementById('results').addEventListener('input',e=>{let x=data.items.find(y=>y.id===e.target.dataset.id);if(x) x[e.target.dataset.field]=e.target.value});
    document.getElementById('results').addEventListener('change',e=>{let x=data.items.find(y=>y.id===e.target.dataset.id);if(x) x[e.target.dataset.field]=e.target.value});
    function exportDecisions(){let d={source_sha256:data.source_sha256,decisions:data.items.filter(x=>x.decision).map(x=>({id:x.id,pdf_page:x.pdf_page,decision:x.decision,label_candidate:x.label_candidate,notes:x.notes||''}))};let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));a.download='engineering_legend_review_decisions.json';a.click()}
    render();</script></html>'''.replace('__STATE__',data)
    (out/'Offline_Legend_Review.html').write_text(html,encoding='utf-8')
    stats={'source_sha256':registry['source_sha256'],'source_pages':len(registry['pages']),'source_candidates':len(items),
           'owner_approved_from_input':sum(bool(x.get('owner_mapping_approved')) for x in items),
           'automatically_approved':0,'overall_library_ready':False,
           'warning':'Source page coverage does not imply symbol-level completeness or engineering approval.'}
    (out/'validation.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    return stats


def main():
    p=argparse.ArgumentParser();p.add_argument('--pdf',required=True);p.add_argument('--registry',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(build_atlas(Path(a.pdf).read_bytes(),json.loads(Path(a.registry).read_text()),Path(a.out)),indent=2))
if __name__=='__main__':main()
