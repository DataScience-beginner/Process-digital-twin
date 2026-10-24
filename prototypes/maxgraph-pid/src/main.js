import '@maxgraph/core/css/common.css';
import './style.css';
import {Graph,InternalEvent,constants} from '@maxgraph/core';
import {source,createModel,validate,insertDischargeValve,stageModel} from './engineering.js';
const elt=id=>document.getElementById(id);
const graphElement=elt('graph');
InternalEvent.disableContextMenu(graphElement);
const graph=new Graph(graphElement);
graph.setPanning(true);
graph.setConnectable(false);
graph.setCellsEditable(false);
const positions={
'inlet-boundary-1':[25,200,85,45],'eq-vessel-1':[145,130,105,165],
'nz-v-1':[285,206,45,38],'pipe-suc-1':[365,205,86,43],
'valve-suc-1':[480,205,85,43],'pipe-suc-2':[595,205,86,43],
'nz-p-s':[715,206,45,38],'eq-pump-1':[800,170,112,112],
'nz-p-d':[950,207,45,38],'pipe-dis-1':[1030,205,83,43],
'valve-dis-1':[1147,205,85,43],'outlet-boundary-1':[1260,205,104,43],
feed:[80,165,190,85],transfer:[390,165,190,85],delivery:[700,165,190,85]
};
let model=createModel(),stage='pid',cells=new Map();
const colors={equipment:'#dbeafe',valve:'#fde68a',nozzle:'#d1fae5',pipe:'#f1f5f9',boundary:'#e2e8f0'};
const styleFor=n=>{
 let fill=colors.boundary,shape='rounded';
 if(n.type==='centrifugal_pump'){fill=colors.equipment;shape='ellipse';}
 else if(n.type==='vertical_separator'){fill=colors.equipment;shape='cylinder';}
 else if(n.type==='isolation_valve'){fill=colors.valve;shape='rhombus';}
 else if(n.type==='process_nozzle'){fill=colors.nozzle;shape='ellipse';}
 else if(n.type==='piping_segment'){fill=colors.pipe;shape='rounded';}
 else if(n.type==='functional_block'){fill='#e0e7ff';shape='rounded';}
 return {shape,fillColor:fill,strokeColor:'#334155',strokeWidth:1.7,fontColor:'#0f172a',fontSize:13,whiteSpace:'wrap',rounded:true,arcSize:16,align:'center',verticalAlign:'middle'};
};
const label=n=>n.type==='piping_segment'?n.id.replace('pipe-','Line '):n.tag;
function render(){
 graph.removeCells(graph.getChildCells(graph.getDefaultParent(),true,true),true);
 cells=new Map(); const subset=stageModel(stage,model);
 graph.batchUpdate(()=>{
  subset.nodes.forEach((n,i)=>{
    const [x,y,w,h]=positions[n.id]||[130+i*112,300,90,45];
    const cell=graph.insertVertex({id:n.id,value:label(n),position:[x,y],size:[w,h],style:styleFor(n)});
    cells.set(n.id,cell);
  });
  subset.edges.forEach(e=>{
   const a=cells.get(e.from.object_id),b=cells.get(e.to.object_id);
   if(a&&b)graph.insertEdge({id:e.id,value:'',source:a,target:b,style:{edgeStyle:'orthogonalEdgeStyle',strokeColor:'#0d9488',strokeWidth:2,endArrow:'block',endSize:7,rounded:true}});
  });
 });
 fitCanvas();
 elt('view-label').textContent=stage==='bfd'?'BFD — functional modules':stage==='pfd'?'PFD — simulation streams':'P&ID — detailed connections';
 const issues=validate(model);
 elt('status').textContent=model.nodes.length+' objects · '+model.edges.length+' directed connections · '+issues.length+' validation issues';
 document.querySelectorAll('.stage').forEach(b=>b.classList.toggle('active',b.id==='stage-'+stage));
 elt('lineage').textContent=JSON.stringify({source:source.event.source_document_id,revision:source.event.revision,configuration:model.configuration.id,simulation_streams:model.source_stream_ids,model_nodes:model.nodes.length,model_edges:model.edges.length},null,2);
}
const dump=(v)=>{const p=document.createElement('pre');p.textContent=JSON.stringify(v,null,2);return p;};
function select(cell){
 const id=cell?.id; const n=model.nodes.find(x=>x.id===id);
 const e=model.edges.find(x=>x.id===id);
 const el=elt('properties'); el.replaceChildren();
 if(!n&&!e){el.textContent='Select a symbol or connection.';return;}
 const title=document.createElement('h4');title.textContent=n?.tag||id;el.append(title);
 el.append(dump(n?{id:n.id,type:n.type,ports:n.ports,origin:n.origin,connected_edges:model.edges.filter(x=>x.from.object_id===id||x.to.object_id===id).map(x=>x.id)}:e));
}
graph.getSelectionModel().addListener('change',()=>select(graph.getSelectionCell()));
for(const s of ['bfd','pfd','pid'])elt('stage-'+s).addEventListener('click',()=>{stage=s;render();elt('activity').textContent='Showing '+s.toUpperCase()+' representation from the same engineering fixture.';});
elt('add-valve').addEventListener('click',()=>{
 stage='pid';const result=insertDischargeValve(model);render();elt('activity').textContent=result.reason;
 if(result.ok)graph.setSelectionCell(cells.get('valve-dis-1'));
});
elt('reset').addEventListener('click',()=>{model=createModel();stage='pid';render();elt('activity').textContent='Graph restored to source fixture.';});
function fitCanvas(){const width=stage==='bfd'?920:1430;const factor=Math.max(0.25,Math.min(1,(graphElement.clientWidth-42)/width));graph.zoomTo(factor);}
elt('zoom-in').onclick=()=>graph.zoomIn();elt('zoom-out').onclick=()=>graph.zoomOut();elt('fit').onclick=fitCanvas;
elt('export').onclick=()=>{const blob=new Blob([JSON.stringify(model,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='BENCH-001-engineering-graph.json';a.click();URL.revokeObjectURL(u);};
elt('engine').textContent='maxGraph '+constants.VERSION+' · Live canvas';
render();window.__pidDemo={model:()=>model,graph,stage:()=>stage,validate:()=>validate(model)};
