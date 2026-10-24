import test from 'node:test';
import assert from 'node:assert/strict';
import source from '../../../docs/forward-pid/fixtures/pfd_input.json' with {type:'json'};
import reference from '../../../docs/forward-pid/fixtures/expected_graph.json' with {type:'json'};
import catalog from '../configurations/pump-transfer.json' with {type:'json'};
import {generateFromPfd} from '../src/generate.js';
import {validate} from '../src/engineering.js';
const copy=o=>structuredClone(o);
test('approved PFD auto-selects configuration and expands to reference graph without a prompt',()=>{
 const r=generateFromPfd(source);
 assert.equal(r.status,'generated');assert.deepEqual(r.graph.nodes,reference.nodes);
 assert.deepEqual(r.graph.edges,reference.edges);
 assert.deepEqual(r.graph.configuration,reference.configuration);
 assert.deepEqual(r.graph.unknown_fields,reference.unknown_fields);
 assert.equal(r.graph.required_human_prompts,0);
 assert.deepEqual(validate(r.graph),[]);
});
test('unapproved PFD blocks generation instead of guessing',()=>{
 const p=copy(source);p.event.approval_status='draft';
 const r=generateFromPfd(p);assert.equal(r.status,'requires_decision');assert.equal(r.graph,null);
 assert.ok(r.exceptions.includes('PFD_NOT_APPROVED'));
});
test('no approved applicable configuration produces exception',()=>{
 const p=copy(source);p.requirements.pump_arrangement='parallel_2x100';
 const r=generateFromPfd(p);assert.equal(r.status,'requires_decision');assert.ok(r.exceptions.includes('NO_APPLICABLE_APPROVED_CONFIGURATION'));
});
test('wrong topology does not silently match',()=>{
 const p=copy(source);p.streams[0].from='missing-equipment';
 const r=generateFromPfd(p);assert.equal(r.status,'requires_decision');assert.ok(r.exceptions.includes('PFD_PROCESS_CONNECTION_MISSING'));
});
test('configuration must be explicitly approved in library',()=>{
 const library=copy(catalog);library.configurations[0].status='draft';
 const r=generateFromPfd(source,library);assert.equal(r.status,'requires_decision');
});
test('unknown pressure, flow, pipe size and spec remain null',()=>{
 const r=generateFromPfd(source);
 assert.equal(r.graph.engineering_values.pressure,null);
 assert.equal(r.graph.engineering_values.flow,null);
 assert.equal(r.graph.engineering_values.pipe_size,null);
 assert.equal(r.graph.engineering_values.pipe_specification,null);
});
