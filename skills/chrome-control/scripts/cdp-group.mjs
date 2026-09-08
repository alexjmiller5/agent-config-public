#!/usr/bin/env node
// Open tabs inside a session's own window + named tab group (creates both on first use).
//   node cdp-group.mjs "<group name>" [url ...]   -> window=<id> group=<id> tabs=<id,...>   (ids of the tabs opened by THIS call)
//   node cdp-group.mjs "<group name>" --close     -> closes the whole session window
//   --port N   drive a dedicated-profile Chrome (Tier 3/4) instead of the real one (Tier 2, DevToolsActivePort + Allow sheet)
//   --ext ID   extension to borrow the tabGroups API from (default: Claude in Chrome); the profile must have it installed
//   --color C  grey|blue|red|yellow|green|pink|purple|cyan|orange (default: derived from the name)
// Every call also sweeps ungrouped tabs in the session window into the group (popups, target=_blank, OAuth
// redirects). Tab/window ids are Chrome session ids - the same ones chrome-cli prints and accepts.
// Mechanism: CDP has no tab-group API, so a hidden target on an installed extension's origin runs chrome.tabs/tabGroups.
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';

const argv = process.argv.slice(2);
const flag = (f) => { const i = argv.indexOf(f); return i < 0 ? null : argv.splice(i, 2)[1]; };
const port = flag('--port'), ext = flag('--ext') ?? 'fcoeoabgfenejglbffodgkkbkcdhcgfn', colorFlag = flag('--color');
const close = argv.includes('--close'); if (close) argv.splice(argv.indexOf('--close'), 1);
const [name, ...urls] = argv;
if (!name) { console.error('usage: cdp-group.mjs "<group name>" [url ...] | --close'); process.exit(1); }
const COLORS = ['blue', 'red', 'yellow', 'green', 'pink', 'purple', 'cyan', 'orange'];
const color = colorFlag ?? COLORS[[...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0) % COLORS.length];

let wsUrl;
if (port) wsUrl = (await (await fetch(`http://127.0.0.1:${port}/json/version`)).json()).webSocketDebuggerUrl;
else { const [p, path] = readFileSync(join(homedir(), 'Library/Application Support/Google/Chrome/DevToolsActivePort'), 'utf8').trim().split('\n'); wsUrl = `ws://127.0.0.1:${p}${path}`; }
const ws = new WebSocket(wsUrl);
if (!port) spawn(join(dirname(fileURLToPath(import.meta.url)), 'cdp-allow'), ['25'], { stdio: 'ignore', detached: true }).unref();
let id = 0; const pending = new Map();
const send = (method, params = {}, sessionId) => new Promise((res, rej) => { const msg = { id: ++id, method, params }; if (sessionId) msg.sessionId = sessionId; pending.set(msg.id, { res, rej }); ws.send(JSON.stringify(msg)); });
ws.onmessage = (e) => { const m = JSON.parse(e.data); const p = pending.get(m.id); if (p) { pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } };
ws.onerror = () => { console.error('cannot connect to Chrome at ' + wsUrl); process.exit(1); };
setTimeout(() => { console.error('timeout (Allow sheet not approved?)'); process.exit(2); }, 40000);

// Runs inside the extension origin. groupId -1 = chrome.tabGroups.TAB_GROUP_ID_NONE (ungrouped).
const body = async ({ name, color, urls, close }) => {
  let g = (await chrome.tabGroups.query({ title: name }))[0];
  if (close) { if (g) await chrome.windows.remove(g.windowId); return { closed: !!g }; }
  const opened = [];
  if (!g) {
    const w = await chrome.windows.create({ url: urls.shift() ?? 'about:blank', focused: false });
    const first = (w.tabs ?? await chrome.tabs.query({ windowId: w.id }))[0].id;
    const gid = await chrome.tabs.group({ tabIds: [first], createProperties: { windowId: w.id } });
    await chrome.tabGroups.update(gid, { title: name, color });
    g = { id: gid, windowId: w.id }; opened.push(first);
  }
  for (const url of urls) opened.push((await chrome.tabs.create({ windowId: g.windowId, url, active: false })).id);
  const stray = (await chrome.tabs.query({ windowId: g.windowId, groupId: -1 })).map((t) => t.id);
  const tabIds = [...new Set([...opened, ...stray])];
  if (tabIds.length) await chrome.tabs.group({ tabIds, groupId: g.id });
  return { window: g.windowId, group: g.id, tabs: opened };
};

ws.onopen = async () => {
  let tid, hidden = true;
  const url = `chrome-extension://${ext}/manifest.json`;
  try { ({ targetId: tid } = await send('Target.createTarget', { url, hidden: true })); }
  catch { hidden = false; ({ targetId: tid } = await send('Target.createTarget', { url, background: true })); }   // Chrome < 130: visible tab, closed below
  const { sessionId } = await send('Target.attachToTarget', { targetId: tid, flatten: true });
  const expression = `(${body})(${JSON.stringify({ name, color, urls, close })})`;
  for (let i = 0; i < 50; i++) {   // the page needs a moment before the extension APIs are bound
    if ((await send('Runtime.evaluate', { expression: 'typeof chrome?.tabGroups', returnByValue: true }, sessionId)).result.value === 'object') break;
    await new Promise((res) => setTimeout(res, 100));
  }
  const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
  await send('Target.closeTarget', { targetId: tid }).catch(() => {});
  if (r.exceptionDetails) { console.error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text, `\n(is extension ${ext} installed on this profile? it must hold the tabGroups permission)`); process.exit(3); }
  const v = r.result.value;
  console.log(close ? `closed=${v.closed}` : `window=${v.window} group=${v.group} tabs=${v.tabs.join(',')}`);
  process.exit(0);
};
