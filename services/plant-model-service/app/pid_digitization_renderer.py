"""Minimal engineering-review workspace for legacy drawing imports."""
def render_pid_digitization_html() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP | Legacy P&amp;ID Digitization</title>
<style>
body{font:15px system-ui,Arial;color:#14273b;margin:0;background:#f1f4f7}
header{padding:16px 24px;background:#12304e;color:white}header a{color:white}
main{max-width:1250px;margin:auto;padding:16px}.card{background:white;border:1px solid #cbd5df;border-radius:7px;padding:16px;margin-bottom:12px}
h2{font-size:18px;margin:0 0 12px}.muted{color:#465f77}.row{display:flex;gap:14px;flex-wrap:wrap;align-items:start}
button,input,select{font-size:15px;padding:9px;min-height:40px}button{background:#174d7b;border:0;color:white;border-radius:5px;cursor:pointer}
button:focus,input:focus,select:focus{outline:2px solid #297bb3}#entries{flex:1;min-width:250px;max-height:540px;overflow:auto}
.entry{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px;border-bottom:1px solid #e2e6eb}
.entry button{background:#edf4fa;color:#14283d;border:1px solid #bdcfe0}
#source{position:relative;flex:2;min-width:270px}#pageImage{width:100%;display:block;border:1px solid #cbd5df}
#mark{position:absolute;border:2px solid #bd1717;background:#ff000022;display:none;pointer-events:none;box-sizing:border-box}
#state{white-space:pre-wrap}pre{max-height:300px;overflow:auto;font-size:12px}
@media(max-width:650px){.row>*{width:100%}#entries{max-height:320px}}
</style></head><body><header><b>Digital BDEP · P&amp;ID Digitization</b> · <a href="/engineering">Engineering Workspace</a></header>
<main><section class="card"><h2>1. Import a legacy P&amp;ID</h2>
<form id="upload"><input type="file" id="pdf" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" required><label><input type="checkbox" id="ocr"> Local OCR for scanned pages</label><button>Extract evidence</button></form>
<p class="muted">Supports PDF, PNG and JPG. Optional local Tesseract OCR. Vector symbol and direct-line graph proposals require engineering verification; no unreviewed data is published.</p>
<p id="state" role="status"></p></section>
<section class="card" id="review" hidden><h2>2. Verify source tag identities</h2>
<div class="row"><label>Page <select id="page"></select></label>
<label>Reviewer ID <input id="reviewer" type="text" placeholder="Engineer ID"></label>
<button id="save" type="button">Save page review</button><button id="draft" type="button">Export plant draft</button></div>
<p id="summary" class="muted"></p><div class="row"><div id="entries"></div>
<div id="source"><img id="pageImage" alt="Original engineering drawing page"><div id="mark"></div></div></div>
<h2>3. Review proposed process connections</h2><p class="muted">Geometric hypotheses only. Accept only after verifying source stroke, endpoints and process direction.</p>
<div id="connections"></div><button id="saveLinks" type="button">Save connection review</button><h2>4. Digital plant draft (not publishable)</h2><pre id="result" aria-live="polite"></pre></section></main><script>
(function(){
var data=null;var el=function(id){return document.getElementById(id)};
function message(s){el('state').textContent=s}
async function api(url,opt){var r=await fetch(url,opt);var value=await r.json().catch(function(){return {}});if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'Request failed');return value}
function highlight(c){var p=data.pages.find(function(p){return p.page===c.page});var b=c.bbox||c.source_bbox;var mark=el('mark');
mark.style.left=(100*b[0]/p.width)+'%';mark.style.top=(100*b[1]/p.height)+'%';
mark.style.width=(100*(b[2]-b[0])/p.width)+'%';mark.style.height=(100*(b[3]-b[1])/p.height)+'%';mark.style.display='block'}
function showPage(n){el('pageImage').src='/api/pid-digitization/imports/'+encodeURIComponent(data.id)+'/pages/'+n+'.png';
el('mark').style.display='none';var entries=el('entries');entries.replaceChildren();
var subset=data.candidates.filter(function(c){return c.page===Number(n)});
subset.forEach(function(c){var row=document.createElement('div');row.className='entry';
var btn=document.createElement('button');btn.type='button';btn.textContent=c.tag;btn.onclick=function(){highlight(c)};
var select=document.createElement('select');select.dataset.id=c.id;
['unreviewed','accepted','rejected'].forEach(function(status){select.add(new Option(status,status))});
select.value=c.review_status;row.append(btn,select);entries.append(row)});
if(!subset.length)entries.textContent='No detected tags on this page.';showLinks(Number(n))}
function display(){el('review').hidden=false;el('summary').textContent=data.candidates.length+' candidate mentions, '+(data.symbol_hypotheses||[]).filter(function(s){return s.geometry_id}).length+' visual matches, '+(data.connection_proposals||[]).length+' unverified connection proposals, '+data.page_count+' pages. '+data.warnings.join(' ');
var p=el('page');var current=p.value;p.replaceChildren();data.pages.forEach(function(page){p.add(new Option('Page '+page.page,page.page))});p.value=current&&data.pages.some(function(x){return String(x.page)===current})?current:'1';showPage(p.value)}
el('upload').onsubmit=async function(event){event.preventDefault();message('Extracting document…');var files=el('pdf').files;if(!files.length)return;
var fd=new FormData();fd.append('file',files[0]);try{data=await api('/api/pid-digitization/imports?ocr='+el('ocr').checked,{method:'POST',body:fd});message('Import saved: '+data.id);display()}catch(e){message(e.message)}};
el('page').onchange=function(){showPage(el('page').value)};
el('save').onclick=async function(){var reviewer=el('reviewer').value.trim();if(reviewer.length<2){message('Provide reviewer ID');return}
var decisions=Array.from(el('entries').querySelectorAll('select')).map(function(s){return {candidate_id:s.dataset.id,decision:s.value}});
if(!decisions.length)return;try{data=await api('/api/pid-digitization/imports/'+encodeURIComponent(data.id)+'/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewer:reviewer,decisions:decisions})});message('Review saved.');display()}catch(e){message(e.message)}};
function showLinks(page){var area=el('connections');area.replaceChildren();
var links=(data.connection_proposals||[]).filter(function(edge){return edge.page===page});
if(!links.length){area.textContent='No direct vector-stroke links proposed for this page. Manual topology review is required.';return}
links.forEach(function(edge){var row=document.createElement('div');row.className='entry';
var btn=document.createElement('button');btn.type='button';btn.textContent=edge.tag_a+' — '+edge.tag_b;btn.onclick=function(){highlight(edge)};
var status=document.createElement('select');status.dataset.id=edge.id;status.className='edge-status';
['unreviewed','accepted','rejected'].forEach(function(v){status.add(new Option(v,v))});status.value=edge.review_status;
var direction=document.createElement('select');direction.className='edge-direction';direction.setAttribute('aria-label','Confirmed flow direction for '+edge.id);
[['unverified','Unverified direction'],['a_to_b',edge.tag_a+' → '+edge.tag_b],['b_to_a',edge.tag_b+' → '+edge.tag_a]].forEach(function(pair){direction.add(new Option(pair[1],pair[0]))});direction.value=edge.direction;
row.append(btn,status,direction);area.append(row)})}
el('saveLinks').onclick=async function(){var reviewer=el('reviewer').value.trim();if(reviewer.length<2){message('Provide reviewer ID');return}
var decisions=Array.from(el('connections').querySelectorAll('.edge-status')).map(function(status){return {proposal_id:status.dataset.id,decision:status.value,direction:status.parentElement.querySelector('.edge-direction').value}});
if(!decisions.length){message('No connection proposals on this page');return}
try{data=await api('/api/pid-digitization/imports/'+encodeURIComponent(data.id)+'/connections/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewer:reviewer,decisions:decisions})});message('Connection review saved.');display()}catch(e){message(e.message)}};
el('draft').onclick=async function(){try{var draft=await api('/api/pid-digitization/imports/'+encodeURIComponent(data.id)+'/plant-draft');el('result').textContent=JSON.stringify(draft,null,2)}catch(e){message(e.message)}};
})();
</script></body></html>"""
