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
#chosen{font-weight:bold}#legendSource{position:relative;max-width:900px;width:100%;touch-action:none}#legendSheet{display:block;width:100%;pointer-events:none;border:1px solid #bec9d3}#legendBox{position:absolute;border:2px solid #e01a18;background:#ff131322;pointer-events:none;display:none;box-sizing:border-box}.badge{padding:4px 8px;border:1px solid #bed0df;border-radius:15px;background:#eaf2f9}
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
<label>PDF drawing files (multiple) or one ZIP archive<input id="files" type="file" accept=".pdf,.zip" multiple required></label>
<button type="submit">Upload and inventory</button></form>
<p class="status" id="status" role="status"></p></section>
<section class="box" id="inventory" hidden>
<h2>Drawing register / legend identification</h2>
<div id="readiness" class="muted"></div>
<div class="flex"><label>Review engineer <input id="reviewer" placeholder="Engineer ID"></label>
<button id="save" type="button">Approve selected page roles</button><label><input type="checkbox" id="batchOcr"> OCR on pages with sparse native tag text (slower)</label><button id="bulk" type="button">Digitize first 10 approved P&amp;IDs</button></div>
<p class="muted">Check every sheet classification. Legend pages build a source-cited
engineering vocabulary; text next to a symbol does not verify the geometry.</p>
<div id="documents"></div><div id="batchResults" class="status"></div></section>
<section class="box" id="legendLibrary" hidden><h2>Project legend symbol examples (human verification)</h2><p class="muted">Each example is a source-linked label and tentative left-side graphic crop. Many crops will be inaccurate. Inspect before accepting; accepted examples are not automatically applied to process drawings.</p><div id="legendItems"></div><div class="flex"><button id="saveLegend" type="button">Save inspected legend examples</button></div><p id="legendHint" class="muted">Select a legend label, then drag a rectangle around its actual graphical symbol on the full sheet. Save the crop before accepting the example.</p><div id="legendSource" hidden><img id="legendSheet" alt="Original source legend sheet" src=""><div id="legendBox"></div></div><p><button id="saveCrop" type="button">Save corrected source symbol box</button></p><img id="legendImage" class="preview" alt="Cropped source legend symbol example" hidden></section>
<section class="box" id="viewer" hidden>
<h2>Source-page inspection</h2>
<p id="chosen"></p><img id="preview" class="preview" alt="Original client P&ID sheet">
<p><button id="analyze" type="button">Extract symbols and graph from this verified P&amp;ID</button></p>
<p class="muted">The extraction creates a draft for human verification. It cannot
automatically publish engineering deliverables.</p>
<pre id="result" class="status"></pre></section>
</main><script>
(function(){
var state=null;var current=null;var selectedLegend=null;var dragStart=null;var cropBox=null;
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
selectedLegend={document:doc,term:item};
var url='/api/pid-digitization/client-batches/'+state.id+'/documents/'+doc.id+'/';
el('legendImage').hidden=false;el('legendImage').src=url+'legends/'+item.id+'.png';
el('legendSource').hidden=false;el('legendSheet').src=url+'pages/'+item.page+'.png';
cropBox=item.reviewed_symbol_bbox_pdf||item.proposed_symbol_crop_pdf;
el('legendHint').textContent='Draw a new crop around the true '+item.label+
' graphical symbol on the source page, then save it. Proposed left-side crop is not verified.';
updateCropOverlay()};
var selector=document.createElement('select');selector.className='legend-role';
selector.dataset.doc=doc.id;selector.dataset.id=item.id;
['unreviewed','accepted','rejected'].forEach(function(v){selector.add(new Option(v,v))});
selector.value=item.review_status;
row.append(btn,selector);area.append(row)})});
el('legendLibrary').hidden=(count===0);
}
function updateCropOverlay(){
if(!selectedLegend||!cropBox)return;
var page=selectedLegend.document.preflight.pages[selectedLegend.term.page-1];
var box=el('legendBox');box.style.left=(cropBox[0]*100/page.width_pts)+'%';
box.style.top=(cropBox[1]*100/page.height_pts)+'%';
box.style.width=((cropBox[2]-cropBox[0])*100/page.width_pts)+'%';
box.style.height=((cropBox[3]-cropBox[1])*100/page.height_pts)+'%';
box.style.display='block'}
function pointerInPage(e){
var rect=el('legendSheet').getBoundingClientRect(),page=selectedLegend.document.preflight.pages[selectedLegend.term.page-1];
return [
Math.max(0,Math.min(page.width_pts,(e.clientX-rect.left)/rect.width*page.width_pts)),
Math.max(0,Math.min(page.height_pts,(e.clientY-rect.top)/rect.height*page.height_pts))
]}
el('legendSource').onpointerdown=function(e){if(!selectedLegend)return;
dragStart=pointerInPage(e);el('legendSource').setPointerCapture(e.pointerId)};
el('legendSource').onpointerup=function(e){if(!dragStart||!selectedLegend)return;
var end=pointerInPage(e);
cropBox=[Math.min(dragStart[0],end[0]),Math.min(dragStart[1],end[1]),
Math.max(dragStart[0],end[0]),Math.max(dragStart[1],end[1])].map(function(n){return Math.round(n*100)/100});
dragStart=null;updateCropOverlay()};
el('saveCrop').onclick=async function(){if(!selectedLegend||!cropBox){msg('Select a legend term and draw a symbol rectangle first');return}
var reviewer=el('reviewer').value.trim();if(reviewer.length<2){msg('Enter reviewer ID first');return}
try{var doc=selectedLegend.document,term=selectedLegend.term;
var url='/api/pid-digitization/client-batches/'+state.id+'/documents/'+doc.id+'/legends/'+term.id;
await call(url+'/crop',{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({reviewer:reviewer,x0:cropBox[0],y0:cropBox[1],x1:cropBox[2],y1:cropBox[3]})});
el('legendImage').src=url+'.png?version='+Date.now();
msg('Source symbol rectangle saved; now accept/reject the visual example separately.');
state=await call('/api/pid-digitization/client-batches/'+state.id);show()}
catch(e){msg(e.message)}};
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
var isZip=files.length===1&&files[0].name.toLowerCase().endsWith('.zip');
if(isZip){body.append('archive',files[0])}
else{for(var i=0;i<files.length;i++){
if(files[i].name.toLowerCase().endsWith('.zip')){msg('Upload a ZIP alone or multiple PDFs');return}
body.append('files',files[i])}}
var route=isZip?'/api/pid-digitization/client-batches/zip':'/api/pid-digitization/client-batches';
try{state=await call(route,{method:'POST',body:body});
msg('Uploaded package '+state.id+'. Review source-page roles and approve legends first.');show()}
catch(err){msg(err.message)}};
el('bulk').onclick=async function(){if(!state){msg('Upload a drawing package first');return}
msg('Running 10 source-linked P&ID extractions sequentially; this may take time…');
try{var result=await call('/api/pid-digitization/client-batches/'+state.id+
'/analyze-approved?limit=10&ocr='+el('batchOcr').checked,{method:'POST'});
var root=el('batchResults');root.replaceChildren();
var note=document.createElement('p');note.textContent=result.processed+' P&ID sheets analyzed. '+
result.remaining_sheets+' remaining. Every result requires engineering review.';root.append(note);
result.results.forEach(function(item){var link=document.createElement('a');
link.href=item.review_url;link.textContent='Source page '+item.source_original_page+
' · '+item.tag_candidates+' tag candidates, '+item.connection_candidates+
' graph proposals'+(item.reused?' (previous analysis)':'');
link.style.display='block';link.target='_blank';root.append(link)});
msg('Source-linked draft extraction complete. No plant-model baseline was modified.')}
catch(e){msg(e.message)}};
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
