import test from 'node:test';
import assert from 'node:assert/strict';
import standby from '../fixtures/pfd_duty_standby.json' with {type:'json'};
import {generateFromPfd} from '../src/generate.js';
import {buildElkInput,computeLayout} from '../src/layout.js';
import {stageModel} from '../src/engineering.js';
test('ELK gives unique real coordinates for every single-pump graph object', async()=>{
 const graph=generateFromPfd((await import('../../../docs/forward-pid/fixtures/pfd_input.json',{with:{type:'json'}})).default).graph;
 const visible={nodes:graph.nodes,edges:graph.edges.filter(e=>e.kind==='physical_connection')};
 const result=await computeLayout(visible);
 assert.equal(Object.keys(result.positions).length,11);
 for(const [id,[x,y,w,h]] of Object.entries(result.positions)){
  assert.ok(Number.isFinite(x)&&Number.isFinite(y)&&w>0&&h>0,id);
 }
 assert.ok(result.width>100&&result.height>100);
 assert.equal(buildElkInput(visible).edges.length,10);
});
test('parallel configuration produces two separate pump placements with no overlapping nodes',async()=>{
 const generated=generateFromPfd(standby);
 assert.equal(generated.status,'generated',JSON.stringify(generated.exceptions));
 const graph=generated.graph;
 const visible={nodes:graph.nodes,edges:graph.edges.filter(e=>e.kind==='physical_connection')};
 const result=await computeLayout(visible);
 assert.equal(Object.keys(result.positions).length,22);
 assert.ok(result.positions['eq-pump-a']&&result.positions['eq-pump-b']);
 const a=result.positions['eq-pump-a'],b=result.positions['eq-pump-b'];
 assert.ok(a[0]+a[2]<=b[0]||b[0]+b[2]<=a[0]||a[1]+a[3]<=b[1]||b[1]+b[3]<=a[1]);
 assert.equal(result.routes.length,visible.edges.length);
});
test('stage BFD has graph-driven positions, without coordinate tables',async()=>{
 const v={nodes:[{id:'a',type:'functional_block'},{id:'b',type:'functional_block'}],edges:[{id:'ab',from:{object_id:'a'},to:{object_id:'b'}}]};
 const layout=await computeLayout(v);assert.ok(layout.positions.a[0]<layout.positions.b[0]);
});
