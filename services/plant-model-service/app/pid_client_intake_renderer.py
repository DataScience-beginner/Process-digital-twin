"""Legend-first multi-file P&ID client package pilot interface."""
def render_pid_client_intake_html() -> str:
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital BDEP | Client P&amp;ID Package Intake</title>
<style>
:root{color-scheme:light}body{margin:0;background:#f4f6f8;color:#17324c;font:15px system-ui,Arial}
header{background:#12314e;padding:16px 24px;color:#fff}header a{color:#eff5ff}
main{max-width:1300px;margin:auto;padding:20px}
h1{font-size:22px;margin:0 0 16px}h2{font-size:17px;margin:0 0 12px}
.box{padding:16px;border:1px solid #cfd8e3;background:#fff;border-radius:8px;margin-bottom:14px}
.flex{display:flex;gap:12px;flex-wrap:wrap;align-items:center}label{display:flex;gap:5px;flex-direction:column}
button,select,input{font:inherit;padding:8px}input[type=file]{max-width:100%}
button{background:#195a8a;color:#fff;border:0;border-radius:5px;cursor:pointer}button:hover{background:#143d68}
#documents{max-height:500px;overflow:auto}.page{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #e5eaf0;flex-wrap:wrap}
.page button{background:#edf4fb;color:#183953;border:1px solid #bed0df}
.page .role{min-width:125px}.muted{color:#55697b}.status{white-space:pre-wrap}
.preview{width:100%;max-width:750px;border:1px solid #ddd}small{color:#516274}
#chosen{font-weight:bold}.badge{padding:4px 8px;border:1px solid #bed0df;border-radius:15px;background:#eaf2f9}
</style></head><body>
<header><strong>Digital BDEP · Client P&amp;ID Package Intake</strong>
&nbsp; | &nbsp;<a href="/engineering">BDEP Engineering Viewer</a></header>
<main><section class="box">
<h1>Upload a client's existing P&amp;ID package</h1>
<p class="muted">Prototype for permission-cleared/public drawings only. Company SSO,
project access rules, encryption and secure storage are not yet implemented.</p>
<form id="upload" class="flex">
<label>Client label<input id="client" required minlength="2" value="Public demonstration"></label>
<label>Drawing package<input id="package" required minlength="2" value="P&amp;ID and legend set"></label>
<label>PDF drawing files (multiple)<input id="files" type="file" accept=".pdf" multiple required></label>
<button type="submit">Upload and inventory</button></form>
<p class="status" id="status" role="status"></p></section>
<section class="box" id="inventory" hidden>
<h2>Drawing register / legend identification</h2>
<div id="readiness" class="muted"></div>
<div class="flex"><label>Review engineer <input id="reviewer" placeholder="Engineer ID"></label>
<button id="save" type="button">Approve selected page roles</button></div>
<p class="muted">Check every sheet classification. Legend pages build a source-cited
engineering vocabulary; text next to a symbol does not verify the geometry.</p>
<div id="documents"></div></section>
<section class="box" id="legendLibrary" hidden><h2>Project legend symbol examples (human verification)</h2><p class="muted">Each example is a source-linked label and tentative left-side graphic crop. Many crops will be inaccurate. Inspect before accepting; accepted examples are not automatically applied to process drawings.</p><div id="legendItems"></div><div class="flex"><button id="saveLegend" type="button">Save inspected legend examples</button></div><img id="legendImage" class="preview" alt="Source-legend proposed symbol crop" hidden></section>
<section class="box" id="viewer" hidden>
<h2>Source-page inspection</h2>
<p id="chosen"></p><img id="preview" class="preview" alt="Original client P&ID sheet">
<p><button id="analyze" type="button">Extract symbols and graph from this verified P&amp;ID</button></p>
<p class="muted">The extraction creates a draft for human verification. It cannot
automatically publish engineering deliverables.</p>
<pre id="result" class="status"></pre></section>
</main><script>
(function(){
var state=null;var current=null;
var el=function(id){return document.getElementById(id)};
function msg(s){el('status').textContent=s}
async function call(url,opts){var r=await fetch(url,opts);var j=await r.json().catch(function(){return {}});
if(!r.ok)throw Error(typeof j.detail==='string'?j.detail:'Request failed ('+r.status+')');return j}
function roleSelect(doc,p){var sel=document.createElement('select');
sel.className='role';sel.dataset.doc=doc.id;sel.dataset.page=p.page;
['legend','pid','index','context','unknown'].forEach(function(v){sel.add(new Option(v,v))});
sel.value=['legend','pid','index','context'].includes(p.role)?p.role:'unknown';
return sel}
function show(){
el('inventory').hidden=false;var root=el('documents');root.replaceChildren();
state.documents.forEach(function(doc){
var h=document.createElement('h3');h.textContent=doc.filename+' — '+doc.preflight.page_count+' sheets';
root.append(h);
doc.preflight.pages.forEach(function(p){
var row=document.createElement('div');row.className='page';
var btn=document.createElement('button');btn.textContent='Inspect sheet '+p.page;
btn.onclick=function(){current={document:doc,page:p.page,role:p.role};
el('viewer').hidden=false;el('chosen').textContent=doc.filename+' | original source page '+p.page+' | '+(p.drawing_numbers||[]).join(', ');
el('preview').src='/api/pid-digitization/client-batches/'+state.id+'/documents/'+doc.id+'/pages/'+p.page+'.png';
el('result').textContent='';el('viewer').scrollIntoView({behavior:'smooth'})};
var role=roleSelect(doc,p);
var title=document.createElement('span');title.className='muted';
title.textContent=(p.drawing_numbers||[]).join(' ')+(p.role_review_status==='accepted'?' · reviewed':' · needs role verification');
row.append(btn,role,title);root.append(row)})
});
readiness();showLegends()}
function showLegends(){var area=el('legendItems');area.replaceChildren();var count=0;
state.documents.forEach(function(doc){(doc.preflight.legend_terms||[]).forEach(function(item){
if(count>=80)return;count++;
var row=document.createElement('div');row.className='page';
var btn=document.createElement('button');btn.type='button';
btn.textContent='Inspect '+item.label+' (sheet '+item.page+')';
btn.onclick=function(){
el('legendImage').hidden=false;
el('legendImage').src='/api/pid-digitization/client-batches/'+state.id+
'/documents/'+doc.id+'/legends/'+item.id+'.png'};
var selector=document.createElement('select');selector.className='legend-role';
selector.dataset.doc=doc.id;selector.dataset.id=item.id;
['unreviewed','accepted','rejected'].forEach(function(v){selector.add(new Option(v,v))});
selector.value=item.review_status;
row.append(btn,selector);area.append(row)})});
el('legendLibrary').hidden=(count===0);
}
el('saveLegend').onclick=async function(){var reviewer=el('reviewer').value.trim();
if(reviewer.length<2){msg('Provide reviewer ID');return}
var decisions=Array.from(el('legendItems').querySelectorAll('.legend-role')).map(function(s){
return {document_id:s.dataset.doc,legend_term_id:s.dataset.id,decision:s.value}});
try{var result=await call('/api/pid-digitization/client-batches/'+state.id+'/legends/review',{
method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({reviewer:reviewer,decisions:decisions})});
state=await call('/api/pid-digitization/client-batches/'+state.id);
msg('Verified '+result.accepted_legend_examples+' proposed legend examples. This is training reference, not automatic symbol detection.');
show()}catch(e){msg(e.message)}};
async function readiness(){
try{var s=await call('/api/pid-digitization/client-batches/'+state.id+'/readiness');
el('readiness').textContent='Legend pages approved: '+s.legend_sheets_approved.length+
' | P&ID pages approved: '+s.pid_sheets_approved.length+' | '+s.readiness}catch(e){msg(e.message)}}
el('upload').onsubmit=async function(e){e.preventDefault();var files=el('files').files;if(!files.length)return;msg('Uploading and classifying drawing sheets…');
var body=new FormData();body.append('client_label',el('client').value);body.append('package_label',el('package').value);
for(var i=0;i<files.length;i++)body.append('files',files[i]);
try{state=await call('/api/pid-digitization/client-batches',{method:'POST',body:body});
msg('Uploaded package '+state.id+'. Review source-page roles and approve legends first.');show()}
catch(err){msg(err.message)}};
el('save').onclick=async function(){var reviewer=el('reviewer').value.trim();if(reviewer.length<2){msg('Enter reviewer ID first');return}
var decisions=Array.from(el('documents').querySelectorAll('select.role')).map(function(s){
return {document_id:s.dataset.doc,page:Number(s.dataset.page),role:s.value}});
try{state=await call('/api/pid-digitization/client-batches/'+state.id+'/roles/review',{
method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({reviewer:reviewer,decisions:decisions})});
msg('Sheet classifications saved with reviewer ID.');show()}catch(e){msg(e.message)}};
el('analyze').onclick=async function(){if(!current){msg('Inspect a drawing first');return}
msg('Running source-grounded extraction; please wait…');
try{var doc=current.document.id;var page=current.page;
var result=await call('/api/pid-digitization/client-batches/'+state.id+
'/documents/'+doc+'/pages/'+page+'/analyze',{method:'POST'});
el('result').textContent=JSON.stringify(result,null,2);
var a=document.createElement('a');a.href=result.review_url;
a.textContent='Open symbol and graph review for this source page';a.style.display='block';
el('result').after(a);msg('Extraction completed; unapproved draft created.')}
catch(err){msg(err.message)}};
var requested=new URLSearchParams(window.location.search).get('batch_id');
if(requested)call('/api/pid-digitization/client-batches/'+encodeURIComponent(requested)).then(function(v){
state=v;msg('Reopened '+state.id);show()}).catch(function(e){msg(e.message)});
})();
</script></body></html>"""
