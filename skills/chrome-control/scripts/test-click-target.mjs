import assert from 'node:assert/strict';
import { clickElement } from './click-target.mjs';

// A scroll causes a late 60px layout shift, as in virtualized list panels.
let reads = 0;
const events = [];
const evaluate = async expr => {
  if (expr.includes('scrollIntoView')) return true;
  return {x: 100, y: ++reads === 1 ? 100 : 160, hit: true, w: 40, h: 20};
};
await clickElement(async (method, params) => { events.push({method,params}); }, evaluate, 'target', 1);
const click = events.find(e => e.params.type === 'mousePressed');
assert.equal(click.params.y, 160, 'Click the settled position, not the pre-scroll rectangle');
await assert.rejects(clickElement(async () => {}, async expr => expr.includes('scrollIntoView') ? true :
  {x: 1, y: 1, w: 20, h: 20, hit: false}, 'target', 1), /obscured|settle/);
console.log('Click layout and occlusion checks passed');
