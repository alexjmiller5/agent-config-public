#!/usr/bin/env node
// Passive CDP network sniffer: attaches to your real logged-in Chrome and
// streams XHR/fetch traffic (with response bodies) as NDJSON while you browse.
//
//   node cdp-sniff.mjs [--url <substr>] [--all] [--secs N] [--raw] > capture.ndjson
//
// Requires: chrome://inspect/#remote-debugging ticked. Click "Allow" when prompted.

import {readFileSync} from 'node:fs';
import {homedir} from 'node:os';
import {join} from 'node:path';

const argv = process.argv.slice(2);
const flag = (n, d) => {const i = argv.indexOf(n); return i === -1 ? d : argv[i + 1];};
const has = n => argv.includes(n);
const urlFilter = flag('--url', '');
const secs = Number(flag('--secs', 300));
const allTypes = has('--all');            // default: only XHR/fetch
const raw = has('--raw');                 // default: redact credentials

const PORT_FILE = process.env.CDP_PORT_FILE ||
  join(homedir(), 'Library/Application Support/Google/Chrome/DevToolsActivePort');

// ponytail: substring match on header name; covers Authorization/Cookie/X-*-Token/api-key.
const SECRET = /auth|cookie|token|session|api[-_]?key|secret|password|csrf|bearer/i;
const mask = v => `<redacted:${String(v).length}b>`;
const clean = h => Object.fromEntries(Object.entries(h || {})
  .map(([k, v]) => [k, !raw && SECRET.test(k) ? mask(v) : v]));

// Credentials also travel in POST BODIES (login forms, token exchanges), which
// headers-only redaction misses entirely. Redact by field name in both JSON
// and form-encoded bodies; if a body can't be parsed but smells like a
// credential, drop it whole rather than risk writing a password to disk.
const BODY_SECRET = /pass(word|code)?|pwd|pin|secret|token|otp|mfa|ssn|answer|credential|auth/i;
const redactDeep = v => Array.isArray(v) ? v.map(redactDeep)
  : (v && typeof v === 'object')
    ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, BODY_SECRET.test(k) ? mask(x) : redactDeep(x)]))
    : v;

function cleanBody(body) {
  if (!body || raw) return body ?? null;
  try {
    return JSON.stringify(redactDeep(JSON.parse(body)));
  } catch {}
  if (/^[^=&\s]+=[^&]*(&|$)/.test(body)) {          // form-encoded
    const p = new URLSearchParams(body);
    for (const k of [...p.keys()]) if (BODY_SECRET.test(k)) p.set(k, mask(p.get(k)));
    return p.toString();
  }
  return BODY_SECRET.test(body) ? mask(body) : body;
}

let port, wsPath;
try {
  [port, wsPath] = readFileSync(PORT_FILE, 'utf8').trim().split('\n');
} catch {
  console.error(`No ${PORT_FILE}.\nTick "Allow remote debugging" at chrome://inspect/#remote-debugging`);
  process.exit(1);
}

const ws = new WebSocket(`ws://127.0.0.1:${port}${wsPath}`);
let id = 0;
const pending = new Map();
// Send a CDP command; sessionId routes it to a page instead of the browser.
const send = (method, params = {}, sessionId) => new Promise(res => {
  const i = ++id;
  pending.set(i, res);
  ws.send(JSON.stringify({id: i, method, params, ...(sessionId && {sessionId})}));
});

const reqs = new Map();   // requestId -> partial record
const sessions = new Set();
let count = 0;

ws.onerror = e => {console.error('ERROR:', e.message ?? e); process.exit(1);};
ws.onclose = e => {console.error(`closed code=${e.code} ${e.reason}`); process.exit(1);};

ws.onopen = async () => {
  console.error('connected; click "Allow" in Chrome if prompted');
  // flatten:true makes child sessions multiplex over this one socket.
  await send('Target.setDiscoverTargets', {discover: true});
  await send('Target.setAutoAttach', {autoAttach: true, waitForDebuggerOnStart: false, flatten: true});
  const {targetInfos} = await send('Target.getTargets');
  for (const t of targetInfos) {
    if (t.type === 'page' && t.url.includes(urlFilter)) {
      await send('Target.attachToTarget', {targetId: t.targetId, flatten: true});
      console.error(`watching: ${t.title.slice(0, 70)}`);
    }
  }
  console.error(`capturing ${allTypes ? 'all' : 'xhr/fetch'} for ${secs}s...`);
};

ws.onmessage = async m => {
  const d = JSON.parse(m.data);
  if (d.id && pending.has(d.id)) {pending.get(d.id)(d.result ?? {}); pending.delete(d.id); return;}

  const s = d.sessionId;
  // GOTCHA: sessionId for a new page arrives in params, not at top level.
  if (d.method === 'Target.attachedToTarget') {
    const sid = d.params.sessionId;
    if (d.params.targetInfo.type === 'page' && !sessions.has(sid)) {
      sessions.add(sid);
      await send('Network.enable', {maxResourceBufferSize: 100e6, maxTotalBufferSize: 200e6}, sid);
    }
    return;
  }
  if (d.method === 'Network.requestWillBeSent') {
    const {requestId, request, type} = d.params;
    reqs.set(requestId, {
      ts: new Date().toISOString(), type, sessionId: s,
      method: request.method, url: request.url,
      requestHeaders: clean(request.headers),
      requestBody: cleanBody(request.postData),
    });
    return;
  }
  if (d.method === 'Network.responseReceived') {
    const r = reqs.get(d.params.requestId);
    if (r) {
      r.type = d.params.type || r.type;
      r.status = d.params.response.status;
      r.mimeType = d.params.response.mimeType;
      r.responseHeaders = clean(d.params.response.headers);
    }
    return;
  }
  if (d.method === 'Network.loadingFinished') {
    const r = reqs.get(d.params.requestId);
    reqs.delete(d.params.requestId);
    if (!r) return;
    if (!allTypes && !['XHR', 'Fetch'].includes(r.type)) return;
    // Body must be fetched on the SAME session, before the page navigates
    // away - Chrome evicts the buffer on navigation.
    const body = await send('Network.getResponseBody', {requestId: d.params.requestId}, r.sessionId);
    r.responseBody = body.base64Encoded ? '<binary>' : (body.body ?? null);
    delete r.sessionId;
    process.stdout.write(JSON.stringify(r) + '\n');
    console.error(`  [${++count}] ${r.status} ${r.method} ${r.url.slice(0, 90)}`);
  }
};

setTimeout(() => {console.error(`done: ${count} requests`); process.exit(0);}, secs * 1000);
