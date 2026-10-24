import ELK from 'elkjs/lib/elk.bundled.js';

const elk = new ELK();
const dimensions = (n) => {
 if(n.type==='vertical_separator')return {width:94,height:142};
 if(n.type==='centrifugal_pump')return {width:104,height:92};
 if(n.type==='junction')return {width:90,height:62};
 if(n.type==='functional_block')return {width:170,height:82};
 if(n.type==='boundary')return {width:104,height:46};
 if(n.type==='process_nozzle')return {width:48,height:38};
 if(n.type==='isolation_valve')return {width:83,height:45};
 return {width:96,height:44};
};

/** A drawing-only projection: graph nodes/edges are never modified by ELK. */
export function buildElkInput(visible) {
 const nodes=visible.nodes.map(n=>({id:n.id,...dimensions(n)}));
 const selected = new Set(nodes.map(n=>n.id));
 const edges=visible.edges
  .filter(e=>e.kind!=='internal_transition')
  .filter(e=>selected.has(e.from.object_id)&&selected.has(e.to.object_id))
  .filter(e=>e.from.object_id!==e.to.object_id)
  .map(e=>({id:e.id,sources:[e.from.object_id],targets:[e.to.object_id]}));
 return {
  id:'drawing-root',
  layoutOptions:{
   'elk.algorithm':'layered',
   'elk.direction':'RIGHT',
   'elk.edgeRouting':'ORTHOGONAL',
   'elk.spacing.nodeNode':'46',
   'elk.layered.spacing.nodeNodeBetweenLayers':'70',
   'elk.layered.nodePlacement.strategy':'NETWORK_SIMPLEX',
   'elk.layered.crossingMinimization.strategy':'LAYER_SWEEP',
   'elk.padding':'[top=30,left=30,bottom=30,right=30]',
  },
  children:nodes,edges
 };
}
export async function computeLayout(visible){
 const result=await elk.layout(buildElkInput(visible));
 const positions=Object.fromEntries(result.children.map(n=>[n.id,[n.x,n.y,n.width,n.height]]));
 for(const n of visible.nodes)if(!positions[n.id])throw new Error('ELK lost node '+n.id);
 return {positions,width:result.width,height:result.height,source:'ELK layered / orthogonal',routes:result.edges.map(e=>({id:e.id,sections:e.sections||[]}))};
}
