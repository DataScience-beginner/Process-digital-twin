"""Offline client-internal reviewer for unapproved glyph+description crop pairs.

The resulting HTML embeds actual client glyph pixels. Keep PRIVATE; this script
itself contains no client source, so may safely live in public GitHub.
"""
from __future__ import annotations
import argparse
import base64
from html import escape
import json
from pathlib import Path


def build_html(manifest: dict, build_folder: Path, *, original_pdf_url: str = "") -> str:
    pairs=[]
    for row in manifest.get("symbols", []):
        ident=row["id"]
        glyph=(build_folder/"source_crops"/f"{ident}_glyph.png").read_bytes()
        label=(build_folder/"source_crops"/f"{ident}_label.png").read_bytes()
        enc=lambda b:"data:image/png;base64,"+base64.b64encode(b).decode("ascii")
        pairs.append({"id":ident,"p":row["page_1based"],"glyph":enc(glyph),"label":enc(label),"warn":row.get("proposal_warning", "")})
    embedded=json.dumps(manifest).replace("<", "\\u003c")
    embedded_pairs=json.dumps(pairs).replace("<", "\\u003c")
    url=json.dumps(original_pdf_url).replace("<", "\\u003c")
    return """<!DOCTYPE html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>Client P&ID Legend — Source-Paired Review</title>
<style>body{font:15px system-ui,Arial;background:#f3f6f9;color:#152232;margin:0}header{position:sticky;top:0;background:white;border-bottom:2px solid #bad0e0;padding:12px 24px;z-index:2;box-shadow:0 1px 4px #ccd}
h1{font-size:22px;margin:0 0 4px}small{color:#5a6172}.stats{font-weight:650;margin:8px 0}main{padding:12px 22px;max-width:1350px;margin:auto}.card{background:white;border:1px solid #bdcbd8;border-radius:9px;margin:11px 0;padding:13px;display:grid;gap:12px;grid-template-columns:130px minmax(200px,1fr) minmax(240px,1.3fr)}.head{font-weight:bold}.pair{border:1px solid #b4c9d8;background:#fff;min-height:65px;padding:10px}.pair img{max-width:100%;image-rendering:auto}.inputs{display:grid;grid-template-columns:1fr 1fr;gap:6px}.inputs label{font-size:12px;font-weight:550}.inputs input,.inputs select{display:block;box-sizing:border-box;width:100%;padding:6px;border:1px solid #acbecd}.warn{color:#af4b00}.buttons{display:flex;gap:8px;flex-wrap:wrap}button{border:0;color:white;padding:10px 13px;border-radius:5px;background:#125c80;cursor:pointer}button.secondary{background:#546678}button:disabled{background:#a0adba}.flag{font-size:12px;color:#8a3b00}a{color:#0076a5}.muted{color:#567}@media(max-width:900px){.card{grid-template-columns:1fr}.inputs{grid-template-columns:1fr}}</style>
<header><h1>Engineering Legend Library — Source-paired symbol mapping</h1><small>Every glyph must be matched to its ACTUAL adjacent description in the source. Not a P&ID recognition demo. Nothing is engineer-approved by default.</small><div class=stats id=stats></div><div class=buttons><button onclick='download()'>Export annotated inventory JSON</button><button class=secondary onclick='window.print()'>Print review sheet</button><a id=src target=_blank></a></div></header>
<main><p><strong>First inspect the original legend:</strong> proposed ink bands may contain two symbols, a cropped glyph, or a line of text. Repair bounding boxes in the manifest when necessary. Red/orange markup from source must be manually separated; do not silently erase it. An 'approved' entry requires two distinct named reviewers and separate confirmations of the glyph isolation and the paired label. Source page completeness is a separate requirement.</p><div id=cards></div></main>
<script>
const manifest=__MANIFEST__;const pairs=__PAIRS__;const source=__SOURCE__;const el=document.getElementById('cards');
if(source){const a=document.getElementById('src');a.href=source;a.textContent='Open original PDF';}
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function update(){const approved=manifest.symbols.filter(s=>s.review_status==='approved').length;const complete=manifest.pages.filter(p=>p.reviewed_complete).length;
document.getElementById('stats').textContent=`${manifest.pages.length} legend pages inventoried • ${complete} pages marked reviewed (NOT certified) • ${manifest.symbols.length} candidate rows • ${approved} user-marked approved entries (compiler will independently validate)`;}
function draw(){el.innerHTML=pairs.map((p,i)=>{const s=manifest.symbols[i];return `<article class=card>
<div class=head>${esc(p.id)}<br>PDF page ${p.p}<div class='flag'>${esc(p.warn)}</div><div class='muted'>Raw ink-row proposal<br>not a verified class</div></div>
<div><b>1. Graphical symbol</b><div class=pair><img src='${p.glyph}' alt='source glyph'></div><label><input data-i=${i} data-key='glyph_isolated_confirmed' type=checkbox ${s.glyph_isolated_confirmed?'checked':''}> Cropped glyph alone matches original</label></div>
<div><b>2. Adjacent original legend text</b><div class=pair><img src='${p.label}' alt='source description crop'></div>
<div class=inputs><label>Exact label from source<input data-i=${i} data-key='label_verbatim' value='${esc(s.label_verbatim)}'></label><label>Canonical engineering class (manual)<input data-i=${i} data-key='class_code' value='${esc(s.class_code)}'></label>
<label><input data-i=${i} data-key='label_paired_confirmed' type=checkbox ${s.label_paired_confirmed?'checked':''}> Label belongs to THIS graphic</label><label>Status<select data-i=${i} data-key='review_status'>${['needs_review','proposed','rejected','approved'].map(st=>`<option value=${st} ${st===s.review_status?'selected':''}>${st}</option>`).join('')}</select></label>
<label>Glyph reviewer<input data-i=${i} data-key='glyph_reviewer' value='${esc(s.glyph_reviewer)}'></label><label>Different independent label reviewer<input data-i=${i} data-key='label_reviewer' value='${esc(s.label_reviewer)}'></label></div></div></article>`}).join('');update();}
el.addEventListener('change',handler);el.addEventListener('input',handler);
function handler(ev){const inp=ev.target;if(!inp.dataset.key)return;const o=manifest.symbols[Number(inp.dataset.i)];o[inp.dataset.key]=inp.type==='checkbox'?inp.checked:inp.value;update();}
function download(){const file=new Blob([JSON.stringify(manifest,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(file);a.download='client_legend_reviewed_manifest.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1500);}
draw();</script></html>""".replace("__MANIFEST__",embedded).replace("__PAIRS__",embedded_pairs).replace("__SOURCE__",url)


def main():
    p=argparse.ArgumentParser();p.add_argument("--manifest",required=True);p.add_argument("--compiled-dir",required=True);p.add_argument("--out",required=True);p.add_argument("--original-url",default="")
    o=p.parse_args();m=json.loads(Path(o.manifest).read_text());Path(o.out).write_text(build_html(m,Path(o.compiled_dir),original_pdf_url=o.original_url),encoding="utf-8")
    print("Saved private review HTML — proposed rows, not approved library")

if __name__=="__main__":main()
