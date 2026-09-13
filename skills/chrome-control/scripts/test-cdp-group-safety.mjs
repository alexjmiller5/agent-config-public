import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
const source=readFileSync(new URL('./cdp-group.mjs',import.meta.url),'utf8');
function context(groups,tabs,{afterUngroup=()=>{}}={}) {
 const removed=[],ungrouped=[],windowsRemoved=[];
 const chrome={tabGroups:{query:async()=>groups},tabs:{query:async filter=>tabs.filter(t=>filter.windowId===undefined?t.groupId===filter.groupId:t.windowId===filter.windowId).map(t=>({...t})),ungroup:async ids=>{ungrouped.push(...ids);for(const t of tabs)if(ids.includes(t.id))t.groupId=-1;afterUngroup(tabs);},remove:async ids=>{for(const id of ids){assert.equal(tabs.find(t=>t.id===id)?.groupId,-1);removed.push(id);}}},windows:{remove:async id=>windowsRemoved.push(id)}};
 const body=vm.runInNewContext(source.slice(source.indexOf('const body ='),source.indexOf('\nws.onopen ='))+'\nbody;',{chrome});
 return {body,removed,ungrouped,windowsRemoved};
}
test('teardown removes only exact grouped tabs and preserves ungrouped tabs in a moved-to window',async()=>{
 const c=context([{id:1,windowId:2}],[{id:3,groupId:1,windowId:2},{id:4,groupId:-1,windowId:2}]);
 await c.body({name:'session',close:true});assert.deepEqual(c.removed,[3]);assert.deepEqual(c.ungrouped,[3]);assert.deepEqual(c.windowsRemoved,[]);
 const missing=context([],[]);await missing.body({name:'missing',close:true});assert.deepEqual(missing.removed,[]);
});
test('duplicate session names never choose an arbitrary group',async()=>{
 const c=context([{id:1,windowId:2},{id:5,windowId:6}],[]);
 await assert.rejects(c.body({name:'same',close:true}),/ambiguous/i);assert.deepEqual(c.removed,[]);
});
test('another group joining the window during teardown cannot lose its tabs',async()=>{
 const c=context([{id:1,windowId:2}],[{id:3,groupId:1,windowId:2}],{afterUngroup:tabs=>tabs.push({id:4,groupId:5,windowId:2})});
 await c.body({name:'session',close:true});assert.deepEqual(c.removed,[3]);assert.deepEqual(c.windowsRemoved,[]);
});
