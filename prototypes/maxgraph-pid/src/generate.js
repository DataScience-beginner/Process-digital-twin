import catalog from '../configurations/pump-transfer.json' with {type:'json'};
import {expandConfiguredParallel} from './generate-parallel.js';
const nodePorts= (ports)=> ports.map((name,i)=>({name,direction:i===0 && ports.length>1?'in':name==='IN' || name==='INLET' || name==='FEED' || name==='SUCTION'?'in':name==='OUT' || name==='OUTLET' || name==='LIQUID' || name==='DISCHARGE'?'out':name==='IN'?'in':'out',kind:'process'}));
const key=(p)=>p.join(':');
export function generateFromPfd(pfd,library=catalog) {
  if(pfd.requirements?.pump_arrangement==='duty_standby')return expandConfiguredParallel(pfd);
  const exceptions=[];
  if(pfd.event?.type!=='pfd.approved'||pfd.event?.approval_status!=='approved')exceptions.push('PFD_NOT_APPROVED');
  const equipment=pfd.objects||[];
  const vessel=equipment.find(n=>n.type==='vertical_separator');
  const pump=equipment.find(n=>n.type==='centrifugal_pump');
  if(!vessel||!pump)exceptions.push('REQUIRED_EQUIPMENT_MISSING');
  const stream=pfd.streams?.find(s=>s.from===vessel?.id&&s.to===pump?.id);
  if(!stream)exceptions.push('PFD_PROCESS_CONNECTION_MISSING');
  const matches=(library.configurations||[]).filter(c=>c.status==='approved'&&
    c.applies_to.section_id===pfd.section_id&&
    c.applies_to.vessel_type===vessel?.type&&
    c.applies_to.pump_type===pump?.type&&
    c.applies_to.phase===stream?.phase&&
    c.applies_to.pump_arrangement===pfd.requirements?.pump_arrangement&&
    c.applies_to.suction_isolation===pfd.requirements?.suction_isolation&&
    c.id===pfd.approved_configuration?.id&&c.version===pfd.approved_configuration?.version);
  if(matches.length!==1)exceptions.push(matches.length?'AMBIGUOUS_CONFIGURATION':'NO_APPLICABLE_APPROVED_CONFIGURATION');
  if(exceptions.length)return {status:'requires_decision',exceptions,graph:null,matched_configuration:null};
  const selected=matches[0];
  const pfdNodes=[
    {id:pfd.interfaces[0].id,tag:'UPSTREAM',type:'boundary'},
    {id:vessel.id,tag:vessel.tag,type:vessel.type},
    ...selected.nodes.filter(n=>['nz-v-1','pipe-suc-1','valve-suc-1','pipe-suc-2','nz-p-s'].includes(n.id)),
    {id:pump.id,tag:pump.tag,type:pump.type},
    ...selected.nodes.filter(n=>['nz-p-d','pipe-dis-1'].includes(n.id)),
    {id:pfd.interfaces[1].id,tag:'DOWNSTREAM',type:'boundary'}
  ];
  const typePorts = {
    'eq-vessel-1':['FEED','LIQUID'],'eq-pump-1':['SUCTION','DISCHARGE'],
    [pfd.interfaces[0].id]:['OUT'],[pfd.interfaces[1].id]:['IN']
  };
  const nodes=pfdNodes.map(n=>({id:n.id,tag:n.tag,type:n.type,
    ports:nodePorts(n.ports||typePorts[n.id]||selected.port_assignments[n.id]||[]),
    origin:{source_id:[vessel.id,pump.id,pfd.interfaces[0].id,pfd.interfaces[1].id].includes(n.id)?n.id:selected.id,source_revision:pfd.event.revision}}));
  const ids=new Set(nodes.map(n=>n.id));
  if(ids.size!==nodes.length)return {status:'requires_decision',exceptions:['DUPLICATE_GENERATED_ID'],graph:null};
  const path=selected.path;
  const edges=path.slice(1).map((to,i)=>{
    const from=path[i];
    return {id:'edge-'+String(i+1).padStart(2,'0'),
      from:{object_id:from[0],port:from[1]},to:{object_id:to[0],port:to[1]},
      kind:from[0]===to[0]?'internal_transition':'physical_connection',
      source_stream_id:i>=path.findIndex(x=>key(x)===selected.stream_break_at)?'str-102':'str-101'};
  });
  const portMap=new Map(nodes.map(n=>[n.id,new Map(n.ports.map(p=>[p.name,p]))]));
  for(const e of edges){
    const a=portMap.get(e.from.object_id)?.get(e.from.port),b=portMap.get(e.to.object_id)?.get(e.to.port);
    if(!a||!b)return {status:'requires_decision',exceptions:['INVALID_CONFIGURATION_PORT'],graph:null};
    const same=e.from.object_id===e.to.object_id;
    if(same!== (e.kind==='internal_transition')||a.direction!==(same?'in':'out')||b.direction!==(same?'out':'in'))
      return {status:'requires_decision',exceptions:['INVALID_CONFIGURATION_DIRECTION'],graph:null};
  }
  return {status:'generated',exceptions:[],matched_configuration:{id:selected.id,version:selected.version},graph:{
    fixture_id:pfd.fixture_id,status:'proposed_validation_pending',
    configuration:{id:selected.id,version:selected.version,approval_basis:'approved_fixture_standard'},
    nodes,edges,expected_path:nodes.map(n=>n.id),source_stream_ids:pfd.streams.map(s=>s.id),
    unknown_fields:pfd.missing_engineering_data,
    engineering_values:Object.fromEntries(pfd.missing_engineering_data.map(k=>[k,null])),
    drawing_geometry:null,required_human_prompts:0
  }};
}
