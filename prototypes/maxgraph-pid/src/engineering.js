import input from '../../../docs/forward-pid/fixtures/pfd_input.json';
import expected from '../../../docs/forward-pid/fixtures/expected_graph.json';
export const source = input;
export const baseline = expected;
export function createModel(){return structuredClone(expected);}
export function validate(model){
 const issues=[], nodes=new Map();
 for(const n of model.nodes){if(nodes.has(n.id))issues.push('Duplicate node '+n.id);nodes.set(n.id,n);}
 const seen=new Set();
 for(const edge of model.edges){
   if(seen.has(edge.id))issues.push('Duplicate edge '+edge.id);seen.add(edge.id);
   const a=nodes.get(edge.from.object_id),b=nodes.get(edge.to.object_id);
   const p=a?.ports.find(x=>x.name===edge.from.port),q=b?.ports.find(x=>x.name===edge.to.port);
   if(!p||!q){issues.push('Missing connection port '+edge.id);continue;}
   if(edge.kind==='physical_connection'&&(a.id===b.id||p.direction!=='out'||q.direction!=='in'))issues.push('Invalid physical edge '+edge.id);
   if(edge.kind==='internal_transition'&&(a.id!==b.id||p.direction!=='in'||q.direction!=='out'))issues.push('Invalid internal transition '+edge.id);
 }
 if(!model.edges.some(x=>x.to.object_id==='outlet-boundary-1'))issues.push('Downstream boundary disconnected');
 return issues;
}
export function insertDischargeValve(model){
 if(model.nodes.some(x=>x.id==='valve-dis-1'))return {ok:false,reason:'Discharge valve already inserted'};
 const edge=model.edges.find(x=>x.id==='edge-19');
 if(!edge)return {ok:false,reason:'Discharge connection is missing'};
 if(edge.from.object_id!=='pipe-dis-1'||edge.to.object_id!=='outlet-boundary-1')return {ok:false,reason:'Unexpected discharge topology'};
 const proposal=structuredClone(model);
 const n={id:'valve-dis-1',tag:'XV-102',type:'isolation_valve',ports:[{name:'INLET',direction:'in',kind:'process'},{name:'OUTLET',direction:'out',kind:'process'}],origin:{source_id:'DEMO_CHANGE_REQUEST',source_revision:'A'}};
 proposal.nodes.push(n);
 const make=(id,from,fp,to,tp,kind)=>({id,from:{object_id:from,port:fp},to:{object_id:to,port:tp},kind,source_stream_id:'str-102'});
 proposal.edges=proposal.edges.filter(x=>x.id!=='edge-19');
 proposal.edges.push(
  make('edge-20','pipe-dis-1','OUTLET','valve-dis-1','INLET','physical_connection'),
  make('edge-21','valve-dis-1','INLET','valve-dis-1','OUTLET','internal_transition'),
  make('edge-22','valve-dis-1','OUTLET','outlet-boundary-1','IN','physical_connection'));
 const errors=validate(proposal);if(errors.length)return {ok:false,reason:errors.join('; ')};
 model.nodes=proposal.nodes;model.edges=proposal.edges;
 return {ok:true,reason:'XV-102 inserted; downstream connection replaced by two physical connections and an internal transition.'};
}
export function stageModel(stage,model){
 if(stage==='pid')return {nodes:model.nodes,edges:model.edges.filter(e=>e.kind==='physical_connection')};
 if(stage==='pfd')return {nodes:model.nodes.filter(n=>['eq-vessel-1','eq-pump-1','outlet-boundary-1'].includes(n.id)),edges:[{id:'pfd-stream-101',from:{object_id:'eq-vessel-1'},to:{object_id:'eq-pump-1'},source_stream_id:'str-101'},{id:'pfd-stream-102',from:{object_id:'eq-pump-1'},to:{object_id:'outlet-boundary-1'},source_stream_id:'str-102'}]};
 return {nodes:[{id:'feed',tag:'Feed preparation',type:'functional_block',ports:[]},{id:'transfer',tag:'Liquid transfer',type:'functional_block',ports:[]},{id:'delivery',tag:'Downstream',type:'functional_block',ports:[]}],edges:[{id:'bfd-1',from:{object_id:'feed'},to:{object_id:'transfer'}},{id:'bfd-2',from:{object_id:'transfer'},to:{object_id:'delivery'}}]};
}
