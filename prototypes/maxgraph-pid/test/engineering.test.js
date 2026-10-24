import test from 'node:test';import assert from 'node:assert/strict';
import {createModel,validate,insertDischargeValve,stageModel} from '../src/engineering.js';
test('fixture 11 nodes 19 edges and no validation errors',()=>{const m=createModel();assert.equal(m.nodes.length,11);assert.equal(m.edges.length,19);assert.deepEqual(validate(m),[]);});
test('stage graph derives BFD PFD P&ID topology',()=>{const m=createModel();assert.equal(stageModel('bfd',m).nodes.length,3);assert.equal(stageModel('pfd',m).edges.length,2);assert.equal(stageModel('pid',m).edges.length,10);});
test('engineering valve insertion changes graph and maintains ports',()=>{const m=createModel();assert.equal(insertDischargeValve(m).ok,true);assert.equal(m.nodes.length,12);assert.equal(m.edges.length,21);assert.deepEqual(validate(m),[]);assert.equal(insertDischargeValve(m).ok,false);});
test('missing physical port fails validation',()=>{const m=createModel();m.edges[0].to.port='FAKE';assert.ok(validate(m).length>0);});
