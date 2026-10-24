import '@maxgraph/core/css/common.css';
import './style.css';
import {Graph,InternalEvent,constants} from '@maxgraph/core';
import {computeLayout} from './layout.js';
import {source,createModel,generateProject,setScenario,scenarioName,validate,insertDischargeValve,stageModel} from './engineering.js';
const elt=id=>document.getElementById(id);
const graphElement=elt('graph');
InternalEvent.disableContextMenu(graphElement);
const graph=new Graph(graphElement);
graph.setPanning(true);
graph.setConnectable(false);
graph.setCellsEditable(false);
let model=createModel(),stage='pid',cells=new Map(),lastLayout=null,renderToken=0;
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
async function render(){
 const token=++renderToken;
 const subset=stageModel(stage,model);
 elt('activity').textContent='Computing ELK layout from graph topology…';
 let layout;
 try{layout=await computeLayout(subset);}catch(error){if(token===renderToken)elt('activity').textContent='Layout failed: '+error.message;throw error;}
 if(token!==renderToken)return;
 lastLayout=layout;
 graph.removeCells(graph.getChildCells(graph.getDefaultParent(),true,true),true);
 cells=new Map();
 graph.batchUpdate(()=>{
  subset.nodes.forEach((n,i)=>{
    const [x,y,w,h]=layout.positions[n.id];
    const cell=graph.insertVertex({id:n.id,value:label(n),position:[x,y],size:[w,h],style:styleFor(n)});
    cells.set(n.id,cell);
  });
  subset.edges.forEach(e=>{
   const a=cells.get(e.from.object_id),b=cells.get(e.to.object_id);
   if(a&&b)graph.insertEdge({id:e.id,value:'',source:a,target:b,style:{edgeStyle:'orthogonalEdgeStyle',strokeColor:'#0d9488',strokeWidth:2,endArrow:'block',endSize:7,rounded:true}});
  });
 });
 fitCanvas();
 elt('activity').textContent='Auto layout complete · '+model.nodes.length+' engineering objects · ELK orthogonal routing.';
 elt('view-label').textContent=stage==='bfd'?'BFD — functional modules':stage==='pfd'?'PFD — simulation streams':'P&ID — detailed connections';
 const issues=validate(model);
 elt('status').textContent=model.nodes.length+' objects · '+model.edges.length+' directed connections · '+issues.length+' validation issues';
 document.querySelectorAll('.stage').forEach(b=>b.classList.toggle('active',b.id==='stage-'+stage));
 elt('lineage').textContent=JSON.stringify({trigger:source.event.type,approval:source.event.approval_status,generated_from:'PFD + approved configuration registry',source:source.event.source_document_id,revision:source.event.revision,configuration:model.configuration.id,simulation_streams:model.source_stream_ids,model_nodes:model.nodes.length,model_edges:model.edges.length},null,2);
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
for(const name of ['single','standby'])elt('scenario-'+name).addEventListener('click',()=>{
 setScenario(name);model=createModel();stage='pid';render();
 elt('activity').textContent='Approved '+source.event.source_document_id+' → '+model.configuration.id+' → '+model.nodes.length+' objects / '+model.edges.length+' connections. Both branches derived from data.';
});
for(const s of ['bfd','pfd','pid'])elt('stage-'+s).addEventListener('click',()=>{stage=s;render();elt('activity').textContent='Showing '+s.toUpperCase()+' representation from the same engineering fixture.';});
elt('regenerate').addEventListener('click',()=>{
 const result=generateProject();
 if(result.status!=='generated'){elt('activity').textContent='Engineering decision required: '+result.exceptions.join(', ');return;}
 model=result.graph;stage='pid';render();
 elt('activity').textContent='Approved PFD '+source.event.source_document_id+' Rev '+source.event.revision+' → matched '+result.matched_configuration.id+' v'+result.matched_configuration.version+' → generated '+model.nodes.length+' engineering objects and '+model.edges.length+' port connections. No human prompt.';
});
elt('add-valve').addEventListener('click',()=>{
 stage='pid';const result=insertDischargeValve(model);render();elt('activity').textContent=result.reason;
 if(result.ok)graph.setSelectionCell(cells.get('valve-dis-1'));
});
elt('reset').addEventListener('click',()=>{model=createModel();stage='pid';render();elt('activity').textContent='Graph restored to source fixture.';});
function fitCanvas(){const width=Math.max(lastLayout?.width||700,1),height=Math.max(lastLayout?.height||450,1);const factor=Math.max(0.15,Math.min(1.5,(graphElement.clientWidth-36)/width,(graphElement.clientHeight-36)/height));graph.zoomTo(factor);}
elt('zoom-in').onclick=()=>graph.zoomIn();elt('zoom-out').onclick=()=>graph.zoomOut();elt('fit').onclick=fitCanvas;
elt('export').onclick=()=>{const blob=new Blob([JSON.stringify(model,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download='BENCH-001-engineering-graph.json';a.click();URL.revokeObjectURL(u);};
elt('engine').textContent='maxGraph '+constants.VERSION+' + ELK · Auto layout';
render();window.__pidDemo={model:()=>model,graph,stage:()=>stage,layout:()=>lastLayout,validate:()=>validate(model)};
