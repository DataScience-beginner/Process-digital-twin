import test from 'node:test';
import assert from 'node:assert/strict';
import pfd from '../fixtures/pfd_duty_standby.json' with {type:'json'};
import catalog from '../configurations/pump-duty-standby.json' with {type:'json'};
import {expandConfiguredParallel} from '../src/generate-parallel.js';
import {validate} from '../src/engineering.js';
const clone=x=>structuredClone(x);
const trace=(graph,start,end)=>{
 const adjacent=new Map();
 for(const e of graph.edges){const a=e.from.object_id,b=e.to.object_id; if(!adjacent.has(a))adjacent.set(a,new Set());adjacent.get(a).add(b);}
 const q=[start],seen=new Set(q);while(q.length){const n=q.shift();if(n===end)return true;for(const next of adjacent.get(n)||[])if(!seen.has(next)){seen.add(next);q.push(next);}}return false;
};
test('two-pump fixture generates 22 nodes with both complete branches',()=>{
 const r=expandConfiguredParallel(pfd);
 assert.equal(r.status,'generated',JSON.stringify(r.exceptions));
 const g=r.graph;
 assert.equal(g.nodes.length,22);
 assert.ok(g.edges.length>30);
 assert.deepEqual(validate(g),[]);
 assert.ok(trace(g,'inlet-boundary-1','eq-pump-a'));
 assert.ok(trace(g,'inlet-boundary-1','eq-pump-b'));
 assert.ok(trace(g,'eq-pump-a','outlet-boundary-1'));
 assert.ok(trace(g,'eq-pump-b','outlet-boundary-1'));
 assert.equal(g.engineering_values.pressure,null);
 assert.equal(g.required_human_prompts,0);
});
test('config detects swapped or absent pump roles',()=>{
 const bad=clone(pfd);bad.objects[2].role='duty_pump';
 assert.equal(expandConfiguredParallel(bad).status,'requires_decision');
});
test('missing standby stream blocks generation',()=>{
 const bad=clone(pfd);bad.streams=bad.streams.filter(x=>x.id!=='str-101B');
 assert.ok(expandConfiguredParallel(bad).exceptions.includes('PFD_PROCESS_CONNECTION_MISSING'));
});
test('unapproved library blocks generation',()=>{
 const bad=clone(catalog);bad.configurations[0].status='draft';
 assert.ok(expandConfiguredParallel(pfd,bad).exceptions.includes('NO_APPLICABLE_APPROVED_CONFIGURATION'));
});
test('invalid template port blocks generation',()=>{
 const bad=clone(catalog);bad.configurations[0].routes[0].steps[3][1]='BAD-PORT';
 assert.ok(expandConfiguredParallel(pfd,bad).exceptions.includes('INVALID_CONFIGURATION_PORT'));
});
test('no approved source revision blocks generation',()=>{
 const bad=clone(pfd);bad.event.approval_status='draft';
 assert.ok(expandConfiguredParallel(bad).exceptions.includes('PFD_NOT_APPROVED'));
});
