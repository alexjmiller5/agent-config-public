#!/usr/bin/env node
// Evaluate one JS expression in the first page target of a CDP Chrome (Tier 3/4).
//   node cdp-eval.mjs <port> '<expression>' [--url <substring>]   -> prints the result value
// Zero deps (Node 22+ WebSocket). One connection per call - no approval dialog on a dedicated profile.
const [port, expr, ...rest] = process.argv.slice(2);
const want = rest.includes('--url') ? rest[rest.indexOf('--url') + 1] : null;
const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const t = list.find(x => x.type === 'page' && (!want || x.url.includes(want)) && !x.url.startsWith('chrome'))
       || list.find(x => x.type === 'page' && !x.url.startsWith('chrome-extension'));
if (!t) { console.error('no page target'); process.exit(1); }
const ws = new WebSocket(t.webSocketDebuggerUrl);
const done = new Promise((res, rej) => {
  ws.onopen = () => ws.send(JSON.stringify({ id: 1, method: 'Runtime.evaluate', params: { expression: expr, returnByValue: true, awaitPromise: true } }));
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id === 1) { ws.close(); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); } };
  ws.onerror = e => rej(new Error('ws error'));
  setTimeout(() => rej(new Error('timeout')), 30000);
});
try { const r = await done; if (r.exceptionDetails) { console.error(r.exceptionDetails.text); process.exit(2); } const v = r.result.value; process.stdout.write(typeof v === 'string' ? v : JSON.stringify(v ?? '')); }
catch (e) { console.error(String(e)); process.exit(1); }
