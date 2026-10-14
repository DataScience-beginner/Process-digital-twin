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
<form id="upload"><input type="file" id="pdf" accept=".pdf,application/pdf" required><button>Extract tag candidates</button></form>
<p class="muted">First MVP: offline PDF text/tag extraction, engineering verification, PDF source coordinates. No OCR or automatic pipe connections yet.</p>
<p id="state" role="status"></p></section>
<section class="card" id="review" hidden><h2>2. Verify source tag identities</h2>
<div class="row"><label>Page <select id="page"></select></label>
<label>Reviewer ID <input id="reviewer" type="text" placeholder="Engineer ID"></label>
<button id="save" type="button">Save page review</button><button id="draft" type="button">Export plant draft</button></div>
<p id="summary" class="muted"></p><div class="row"><div id="entries"></div>
<div id="source"><img id="pageImage" alt="Original engineering drawing page"><div id="mark"></div></div></div>
<pre id="result" aria-live="polite"></pre></section></main><script>
(function(){
var data=null;var el=function(id){return document.getElementById(id)};
function message(s){el('state').textContent=s}
async function api(url,opt){var r=await fetch(url,opt);var value=await r.json().catch(function(){return {}});if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'Request failed');return value}
function highlight(c){var p=data.pages.find(function(p){return p.page===c.page});var b=c.bbox;var mark=el('mark');
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
if(!subset.length)entries.textContent='No detected tags on this page.'}
function display(){el('review').hidden=false;el('summary').textContent=data.candidates.length+' candidate mentions, '+data.page_count+' pages. '+data.warnings.join(' ')+' — Connectivity not reconstructed.';
var p=el('page');var current=p.value;p.replaceChildren();data.pages.forEach(function(page){p.add(new Option('Page '+page.page,page.page))});p.value=current&&data.pages.some(function(x){return String(x.page)===current})?current:'1';showPage(p.value)}
el('upload').onsubmit=async function(event){event.preventDefault();message('Extracting document…');var files=el('pdf').files;if(!files.length)return;
var fd=new FormData();fd.append('file',files[0]);try{data=await api('/api/pid-digitization/imports',{method:'POST',body:fd});message('Import saved: '+data.id);display()}catch(e){message(e.message)}};
el('page').onchange=function(){showPage(el('page').value)};
el('save').onclick=async function(){var reviewer=el('reviewer').value.trim();if(reviewer.length<2){message('Provide reviewer ID');return}
var decisions=Array.from(el('entries').querySelectorAll('select')).map(function(s){return {candidate_id:s.dataset.id,decision:s.value}});
if(!decisions.length)return;try{data=await api('/api/pid-digitization/imports/'+encodeURIComponent(data.id)+'/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reviewer:reviewer,decisions:decisions})});message('Review saved.');display()}catch(e){message(e.message)}};
el('draft').onclick=async function(){try{var draft=await api('/api/pid-digitization/imports/'+encodeURIComponent(data.id)+'/plant-draft');el('result').textContent=JSON.stringify(draft,null,2)}catch(e){message(e.message)}};
})();
</script></body></html>"""
