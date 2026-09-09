#!/usr/bin/env node
// Evaluate one JS expression in the first page target of a CDP Chrome (Tier 3/4).
//   node cdp-eval.mjs <port> '<expression>' [--url <substring>]   -> prints the result value
//   node cdp-eval.mjs <port> --new-window <url>          -> opens a new WINDOW, prints its targetId
//   any mode: --target <targetId> addresses that page instead of the first --url match (parallel drivers)
//   node cdp-eval.mjs <port> --shot /path.png [--url <substring>]   -> Page.captureScreenshot of that page
//   node cdp-eval.mjs <port> --click '<expr returning an Element>' [--url <substring>]
//       -> scrolls it into view and sends a TRUSTED mouse click at its centre (Input.dispatchMouseEvent);
//          prints the click point. Use for controls that ignore synthetic .click() (Chrome 152+ Maps picker rows).
// Zero deps (Node 22+ WebSocket). One connection per call - no approval dialog on a dedicated profile.
import { clickElement } from './click-target.mjs';
const argv = process.argv.slice(2);
const port = argv[0];
const clickMode = argv.includes('--click');
const shotPath = argv.includes('--shot') ? argv[argv.indexOf('--shot') + 1] : null;
const targetId = argv.includes('--target') ? argv[argv.indexOf('--target') + 1] : null;
const newWin = argv.includes('--new-window') ? argv[argv.indexOf('--new-window') + 1] : null;
const expr = clickMode ? argv[argv.indexOf('--click') + 1] : ((shotPath || newWin) ? '1' : argv[1]);
const rest = argv.slice(1);
const want = rest.includes('--url') ? rest[rest.indexOf('--url') + 1] : null;
if (newWin) {   // open a NEW WINDOW (not a tab) and print its targetId - one window per parallel driver
  const ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const bws = new WebSocket(ver.webSocketDebuggerUrl);
  await new Promise((res, rej) => { bws.onopen = res; bws.onerror = rej; });
  bws.send(JSON.stringify({ id: 1, method: 'Target.createTarget', params: { url: newWin, newWindow: true } }));
  const tid = await new Promise(res => { bws.onmessage = e => { const m = JSON.parse(e.data); if (m.id === 1) res(m.result.targetId); }; });
  bws.close(); process.stdout.write(tid); process.exit(0);
}
const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const t = targetId ? list.find(x => x.id === targetId && x.type === 'page')
  : list.find(x => x.type === 'page' && (!want || x.url.includes(want)) && !x.url.startsWith('chrome'));
if (!t) { console.error(targetId ? 'target not found: ' + targetId : 'no matching page target'); process.exit(1); }
const ws = new WebSocket(t.webSocketDebuggerUrl);
let nextId = 0; const pending = new Map();
const send = (method, params) => new Promise((res, rej) => { const id = ++nextId; pending.set(id, { res, rej }); ws.send(JSON.stringify({ id, method, params })); });
const opened = new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws error')); });
ws.onmessage = e => { const m = JSON.parse(e.data); const p = pending.get(m.id); if (p) { pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } };
setTimeout(() => { console.error('timeout'); process.exit(1); }, 30000).unref();
const done = (async () => {
  await opened;
  if (shotPath) { const { data } = await send('Page.captureScreenshot', { format: 'png' }); (await import('node:fs')).writeFileSync(shotPath, Buffer.from(data, 'base64')); return { result: { value: 'shot ' + shotPath } }; }
  if (!clickMode) return send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  await send('Page.bringToFront', {}).catch(() => {}); await send('Emulation.setFocusEmulationEnabled', { enabled: true }).catch(() => {});
  const c = await clickElement(send, async expression => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true });
    if (r.exceptionDetails) throw Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  }, expr);
  return { result: { value: `clicked@${Math.round(c.x)},${Math.round(c.y)}` } };
})();
try { const r = await done; if (r.exceptionDetails) { console.error(r.exceptionDetails.text); process.exit(2); } const v = r.result.value; process.stdout.write(typeof v === 'string' ? v : JSON.stringify(v ?? '')); process.exit(0); }
catch (e) { console.error(String(e)); process.exit(1); }
