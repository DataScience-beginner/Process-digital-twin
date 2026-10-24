import dutyStandby from '../configurations/pump-duty-standby.json' with {type:'json'};

const inlet = p => /^(IN|INLET|FEED|SUCTION)(-|$)/.test(p);
const outlet = p => /^(OUT|OUTLET|LIQUID|DISCHARGE)(-|$)/.test(p);
const makePort = p => {
  const direction=inlet(p)?'in':outlet(p)?'out':null;
  if(!direction)throw new Error('Unsupported port direction: '+p);
  return {name:p,direction,kind:'process'};
};
const reject=(...exceptions)=>({status:'requires_decision',exceptions,graph:null,matched_configuration:null});
export function expandConfiguredParallel(pfd, library=dutyStandby) {
  if(pfd.event?.type!=='pfd.approved'||pfd.event?.approval_status!=='approved')return reject('PFD_NOT_APPROVED');
  const selected=(library.configurations||[]).filter(c=>
    c.status==='approved'&&c.id===pfd.approved_configuration?.id&&c.version===pfd.approved_configuration?.version&&
    c.applies_to.section_id===pfd.section_id&&c.applies_to.pump_arrangement===pfd.requirements?.pump_arrangement&&
    c.applies_to.suction_isolation===pfd.requirements?.suction_isolation);
  if(selected.length!==1)return reject(selected.length?'AMBIGUOUS_CONFIGURATION':'NO_APPLICABLE_APPROVED_CONFIGURATION');
  const config=selected[0];
  const objects=pfd.objects||[];
  const vessel=objects.filter(o=>o.type===config.applies_to.vessel_type);
  const pumpA=objects.filter(o=>o.role==='duty_pump'&&o.type===config.applies_to.pump_type);
  const pumpB=objects.filter(o=>o.role==='standby_pump'&&o.type===config.applies_to.pump_type);
  if(vessel.length!==1||pumpA.length!==1||pumpB.length!==1||new Set([vessel[0]?.id,pumpA[0]?.id,pumpB[0]?.id]).size!==3)return reject('UNRESOLVED_EQUIPMENT_ROLES');
  const ids={vessel:vessel[0].id,duty_pump:pumpA[0].id,standby_pump:pumpB[0].id,inlet:pfd.interfaces?.[0]?.id,outlet:pfd.interfaces?.[1]?.id};
  if(!ids.inlet||!ids.outlet||ids.inlet===ids.outlet)return reject('MISSING_PROJECT_INTERFACES');
  const streams=pfd.streams||[];
  for(const name of ['duty_pump','standby_pump']){
    const pumpId=ids[name];
    if(!streams.some(s=>s.from===ids.vessel&&s.to===pumpId&&s.phase===config.applies_to.phase)||!streams.some(s=>s.from===pumpId&&s.to===ids.outlet&&s.phase===config.applies_to.phase))return reject('PFD_PROCESS_CONNECTION_MISSING');
  }
  const generated=config.generated_nodes||[];
  const sourceNodes=[
    {id:ids.inlet,tag:'UPSTREAM',type:'boundary',ports:['OUT']},
    {id:ids.vessel,tag:vessel[0].tag,type:vessel[0].type,ports:['FEED','LIQUID']},
    {id:ids.duty_pump,tag:pumpA[0].tag,type:pumpA[0].type,ports:['SUCTION','DISCHARGE']},
    {id:ids.standby_pump,tag:pumpB[0].tag,type:pumpB[0].type,ports:['SUCTION','DISCHARGE']},
    {id:ids.outlet,tag:'DOWNSTREAM',type:'boundary',ports:['IN']}
  ];
  const combined=[...sourceNodes,...generated];
  if(new Set(combined.map(n=>n.id)).size!==combined.length)return reject('DUPLICATE_NODE_ID');
  let nodes;
  try {
    nodes=combined.map(n=>({...n,ports:n.ports.map(p=>typeof p==='string'?makePort(p):p),origin:{source_id:sourceNodes.some(s=>s.id===n.id)?n.id:config.id,source_revision:pfd.event.revision}}));
  }catch{return reject('CONFIGURATION_PORT_SCHEMA_INVALID');}
  const byId=new Map(nodes.map(n=>[n.id,n]));
  const edges=[],dedup=new Map();
  let sequence=0;
  for(const route of config.routes){
    if(!streams.some(s=>s.id===route.stream_id))return reject('MISSING_ROUTE_STREAM');
    const path=route.steps.map(([id,port])=>({object_id:id.startsWith('$')?ids[id.slice(1)]:id,port}));
    if(path.some(p=>!byId.has(p.object_id)||!byId.get(p.object_id).ports.some(q=>q.name===p.port)))return reject('INVALID_CONFIGURATION_PORT');
    for(let i=1;i<path.length;i++){
      const a=path[i-1],b=path[i],kind=a.object_id===b.object_id?'internal_transition':'physical_connection';
      const start=byId.get(a.object_id).ports.find(p=>p.name===a.port),end=byId.get(b.object_id).ports.find(p=>p.name===b.port);
      if(start.direction!==(kind==='internal_transition'?'in':'out')||end.direction!==(kind==='internal_transition'?'out':'in'))return reject('INVALID_CONFIGURATION_DIRECTION');
      const key=JSON.stringify([a,b]);
      const prior=dedup.get(key);
      if(prior){if(prior.kind!==kind)return reject('CONFLICTING_ROUTE_EDGE');continue;}
      const e={id:'parallel-edge-'+String(++sequence).padStart(2,'0'),from:a,to:b,kind,source_stream_id:route.stream_id};
      edges.push(e);dedup.set(key,e);
    }
  }
  const graph={fixture_id:pfd.fixture_id,status:'proposed_validation_pending',
    configuration:{id:config.id,version:config.version,approval_basis:'approved_fixture_standard'},
    nodes,edges,expected_path:[],source_stream_ids:streams.map(s=>s.id),
    unknown_fields:pfd.missing_engineering_data||[],
    engineering_values:Object.fromEntries((pfd.missing_engineering_data||[]).map(k=>[k,null])),
    drawing_geometry:null,required_human_prompts:0};
  return {status:'generated',exceptions:[],matched_configuration:{id:config.id,version:config.version},graph};
}
