#!/usr/bin/env node
// Trusted input + request capture against the real, logged-in Chrome (Tier 2).
// One WebSocket connection = one "Allow remote debugging?" click by the user.
//
//   node cdp-act.mjs --url <tab-url-substring> [--secs N] < steps.json
//   node cdp-act.mjs --url <substr> --follow <file> [--secs N]   # persistent: one Allow click,
//        then append one JSON step per line to <file>; results stream to stdout; {"quit":true} ends.
//
// steps.json: an array of steps, run in order. Each step is one of
//   {"eval": "<js expression>"}                       -> prints the result
//   {"click": "<js expr returning an Element>"}       -> trusted mouse click at its center
//   {"type": "<text>"}                                -> Input.insertText into the focused element
//   {"key": "Enter"|"Escape"|"Tab"}                   -> trusted key press
//   {"keys": "<text>"}                                -> per-character trusted keyDown/char/keyUp (for editors that ignore insertText)
//   {"shot": "<png path>"}                            -> Page.captureScreenshot of the tab
//   {"sleep": <ms>}
//   {"capture": "<url substring>"}                    -> from here on, print POST bodies of matching requests
// Output is NDJSON: {"step":i, ...result}. Zero dependencies (Node 22+ global WebSocket).
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1] ?? true] : []).filter(Boolean));
const [port, path] = readFileSync(join(homedir(), 'Library/Application Support/Google/Chrome/DevToolsActivePort'), 'utf8').trim().split('\n');
const steps = args.follow ? null : JSON.parse(readFileSync(0, 'utf8'));
const secs = Number(args.secs ?? 600);

const ws = new WebSocket(`ws://127.0.0.1:${port}${path}`);
let id = 0; const pending = new Map(); const listeners = [];
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const msg = { id: ++id, method, params }; if (sessionId) msg.sessionId = sessionId;
  pending.set(msg.id, { res, rej }); ws.send(JSON.stringify(msg));
});
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); }
  else listeners.forEach((l) => l(m));
};
const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
setTimeout(() => { out({ fatal: 'timeout' }); process.exit(2); }, secs * 1000);

ws.onopen = async () => {
  const { targetInfos } = await send('Target.getTargets');
  const t = targetInfos.find((x) => x.type === 'page' && x.url.includes(args.url));
  if (!t) { out({ fatal: 'no tab matching ' + args.url, tabs: targetInfos.filter((x) => x.type === 'page').map((x) => x.url.slice(0, 80)) }); process.exit(1); }
  const { sessionId } = await send('Target.attachToTarget', { targetId: t.targetId, flatten: true });
  const S = (m, p) => send(m, p, sessionId);
  await S('Runtime.enable'); await S('Network.enable'); await S('Page.enable');
  let capture = null; const seen = new Map();
  listeners.push(async (m) => {
    if (m.sessionId !== sessionId || !capture) return;
    if (m.method === 'Network.requestWillBeSent' && m.params.request.url.includes(capture)) seen.set(m.params.requestId, m.params.request);
    if (m.method === 'Network.loadingFinished' && seen.has(m.params.requestId)) {
      const req = seen.get(m.params.requestId); seen.delete(m.params.requestId);
      let postData = req.postData; try { if (!postData && req.hasPostData) postData = (await S('Network.getRequestPostData', { requestId: m.params.requestId })).postData; } catch {}
      let body = ''; try { body = (await S('Network.getResponseBody', { requestId: m.params.requestId })).body; } catch {}
      out({ captured: req.url.slice(0, 300), postData: postData?.slice(0, 6000), response: body.slice(0, 3000) });
    }
  });
  const ev = async (expr) => { const r = await S('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description ?? '')); return r.result.value; };
  const center = async (expr) => ev(`(()=>{const el=(${expr}); if(!el) return null; el.scrollIntoView({block:'center'}); const r=el.getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2,w:r.width,h:r.height}})()`);
  const click = async ({ x, y }) => {
    await S('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    await S('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await S('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  };
  const KEYS = { Enter: { key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' }, Escape: { key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }, Tab: { key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 } };
  const run = async (i, st) => {
      if (st.eval !== undefined) out({ step: i, eval: await ev(st.eval) });
      else if (st.click !== undefined) { const c = await center(st.click); if (!c) { out({ step: i, click: 'ELEMENT NOT FOUND' }); return; } await sleep(150); await click(c); out({ step: i, clicked: c }); }
      else if (st.type !== undefined) { await S('Input.insertText', { text: st.type }); out({ step: i, typed: st.type.length }); }
      else if (st.key !== undefined) { const k = KEYS[st.key]; await S('Input.dispatchKeyEvent', { type: 'keyDown', ...k }); await S('Input.dispatchKeyEvent', { type: 'keyUp', ...k }); out({ step: i, key: st.key }); }
      else if (st.keys !== undefined) { for (const ch of st.keys) { const vk = ch.toUpperCase().charCodeAt(0); await S('Input.dispatchKeyEvent', { type: 'keyDown', key: ch, windowsVirtualKeyCode: vk }); await S('Input.dispatchKeyEvent', { type: 'char', text: ch, unmodifiedText: ch, key: ch }); await S('Input.dispatchKeyEvent', { type: 'keyUp', key: ch, windowsVirtualKeyCode: vk }); await sleep(25); } out({ step: i, keys: st.keys.length }); }
      else if (st.shot !== undefined) { const { data } = await S('Page.captureScreenshot', { format: 'png' }); (await import('node:fs')).writeFileSync(st.shot, Buffer.from(data, 'base64')); out({ step: i, shot: st.shot }); }
      else if (st.sleep !== undefined) await sleep(st.sleep);
      else if (st.capture !== undefined) { capture = st.capture; out({ step: i, capturing: capture }); }
      else if (st.quit) { await sleep(1500); await send('Target.detachFromTarget', { sessionId }).catch(() => {}); process.exit(0); }
  };
  try {
    if (steps) { for (const [i, st] of steps.entries()) await run(i, st); await sleep(1500); }
    else {
      out({ ready: true, follow: args.follow });
      let done = 0;
      for (;;) {
        let lines = []; try { lines = readFileSync(args.follow, 'utf8').split('\n').filter(Boolean); } catch {}
        while (done < lines.length) { const i = done++; try { await run(i, JSON.parse(lines[i])); } catch (e) { out({ step: i, error: String(e) }); } }
        await sleep(300);
      }
    }
  } catch (e) { out({ fatal: String(e) }); }
  await send('Target.detachFromTarget', { sessionId }).catch(() => {});
  process.exit(0);
};
ws.onerror = (e) => { out({ fatal: 'ws error ' + (e.message ?? '') }); process.exit(1); };
