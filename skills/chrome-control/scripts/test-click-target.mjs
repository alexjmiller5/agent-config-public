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
// Lazy-loaded rows can push the requested element outside the viewport again.
let scrolls = 0;
await clickElement(async () => {}, async expr => {
  if (expr.includes('scrollIntoView')) { scrolls++; return true; }
  return {x: 100, y: scrolls < 3 ? 1500 : 200, w: 40, h: 20,
    outside: scrolls < 3, hit: scrolls >= 3};
}, 'target', 1);
assert.equal(scrolls, 3);
console.log('Click layout and occlusion checks passed');

// Optional real-DOM regression: node test-click-target.mjs <dedicated-profile port>.
// Use the actual generated expression and trusted input, not mocked hit results.
if (process.argv[2]) {
  const { execFile } = await import('node:child_process');
  const { promisify } = await import('node:util');
  const { randomUUID } = await import('node:crypto');
  const run = promisify(execFile), port = process.argv[2];
  const group = `click-shadow-test-${randomUUID()}`;
  const groupScript = new URL('./cdp-group.mjs', import.meta.url).pathname;
  let ws;
  try {
    const opened = await run(process.execPath, [groupScript, group, 'about:blank', '--port', port]);
    const targetId = opened.stdout.match(/targets=(\S+)/)[1];
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    ws = new WebSocket(targets.find(t => t.id === targetId).webSocketDebuggerUrl);
    await new Promise((resolve,reject) => { ws.onopen=resolve; ws.onerror=reject; });
    let id=0; const pending=new Map();
    ws.onmessage=event=>{
      const message=JSON.parse(event.data),request=pending.get(message.id);
      if(!request) return;
      pending.delete(message.id);
      message.error ? request.reject(Error(message.error.message)) : request.resolve(message.result);
    };
    const send=(method,params={})=>new Promise((resolve,reject)=>{
      pending.set(++id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));
    });
    const evaluate=async expression=>{
      const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
      if(result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
      return result.result.value;
    };
    await send('Page.bringToFront');
    const cases=[
      ['light DOM descendant',`document.body.innerHTML='<button id="target"><span>Click</span></button>';globalThis.target=document.querySelector('#target');`,true],
      ['shadow toolbar button',`const host=document.createElement('div');document.body.append(host);host.attachShadow({mode:'open'}).innerHTML='<button id="target" style="width:128px;height:36px">Load fixture</button>';globalThis.target=host.shadowRoot.querySelector('#target');`,true],
      ['nested shadow button',`const outer=document.createElement('div');document.body.append(outer);const inner=document.createElement('div');outer.attachShadow({mode:'open'}).append(inner);inner.attachShadow({mode:'open'}).innerHTML='<button id="target"><span>Click</span></button>';globalThis.target=inner.shadowRoot.querySelector('#target');`,true],
      ['target owns a shadow descendant',`const host=document.createElement('div');document.body.append(host);host.attachShadow({mode:'open'}).innerHTML='<span>Click inside</span>';host.style.cssText='display:inline-block;padding:20px';globalThis.target=host;`,true],
      ['slotted descendant',`const host=document.createElement('div');document.body.append(host);host.attachShadow({mode:'open'}).innerHTML='<slot style="display:inline-block"></slot>';host.innerHTML='<button>Slotted button</button>';globalThis.target=host.shadowRoot.querySelector('slot');`,true],
      ['overlay inside same shadow root',`const host=document.createElement('div');document.body.append(host);host.attachShadow({mode:'open'}).innerHTML='<button id="target">Blocked</button><div style="position:fixed;inset:0;z-index:99">Overlay</div>';globalThis.target=host.shadowRoot.querySelector('#target');`,false],
      ['overlay outside shadow root',`const host=document.createElement('div');document.body.append(host);host.attachShadow({mode:'open'}).innerHTML='<button id="target">Blocked</button>';globalThis.target=host.shadowRoot.querySelector('#target');const overlay=document.createElement('div');overlay.style.cssText='position:fixed;inset:0;z-index:99';document.body.append(overlay);`,false],
      ['host hit is not proof of inner target',`const host=document.createElement('div');document.body.append(host);host.style.cssText='display:inline-block;padding:20px';host.attachShadow({mode:'open'}).innerHTML='<button id="target" style="pointer-events:none">Disabled hit</button>';globalThis.target=host.shadowRoot.querySelector('#target');`,false],
    ];
    const failures=[];
    for(const [name,setup,allowed] of cases) {
      await evaluate(`(()=>{document.body.innerHTML='';${setup};globalThis.clicked=0;target.addEventListener('click',event=>{if(event.isTrusted)globalThis.clicked++});return true})()`);
      const dispatched=[];
      const input=async(method,params)=>{dispatched.push(params);return send(method,params);};
      try {
        if(allowed) {
          await clickElement(input,evaluate,'globalThis.target',10);
          assert.equal(await evaluate('globalThis.clicked'),1,`${name}: real trusted click reaches target`);
          assert.equal(dispatched.filter(p=>p.type==='mousePressed').length,1);
        } else {
          await assert.rejects(clickElement(input,evaluate,'globalThis.target',1),/obscured|settle/);
          assert.equal(dispatched.length,0,`${name}: blocked target sends no input`);
          assert.equal(await evaluate('globalThis.clicked'),0);
        }
        console.log(`PASS ${name}`);
      } catch(error) {failures.push(`${name}: ${error.message}`);}
    }
    assert.deepEqual(failures,[],'Real shadow DOM hit-testing');
    console.log('Real browser shadow DOM and obstruction checks passed');
  } finally {
    ws?.close();
    const closed=await run(process.execPath,[groupScript,group,'--close','--port',port]);
    assert.match(closed.stdout,/closed=true/,'Owned browser test group cleaned up');
  }
}
