// Live check: node test-cdp-group.mjs <dedicated-profile port>
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { randomUUID } from 'node:crypto';

const port = process.argv[2];
assert.ok(port, 'Pass the dedicated-profile CDP port');
const run = promisify(execFile);
const script = new URL('./cdp-group.mjs', import.meta.url).pathname;
const name = `group-cleanup-test-${randomUUID()}`;
const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
const ws = new WebSocket(version.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
let id = 0;
const pending = new Map();
ws.onmessage = event => {
  const message = JSON.parse(event.data), request = pending.get(message.id);
  if (!request) return;
  pending.delete(message.id);
  message.error ? request.reject(Error(message.error.message)) : request.resolve(message.result);
};
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
  pending.set(++id, { resolve, reject });
  ws.send(JSON.stringify({ id, method, params, sessionId }));
});
const targets = [];
const attach = async url => {
  const { targetId } = await send('Target.createTarget', { url, hidden: true });
  targets.push(targetId);
  return (await send('Target.attachToTarget', { targetId, flatten: true })).sessionId;
};
const evaluate = async (sessionId, expression) => {
  const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId);
  if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
  return result.result.value;
};
let extension, windowId, observerWindow;
try {
  extension = await attach('chrome-extension://fcoeoabgfenejglbffodgkkbkcdhcgfn/manifest.json');
  for (let i = 0; i < 50; i++) {
    if (await evaluate(extension, 'typeof chrome.tabGroups === "object"')) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const observer = await run(process.execPath, [script, `${name}-observer`, 'chrome://sync-internals/', '--port', port]);
  observerWindow = Number(observer.stdout.match(/window=(\d+)/)[1]);
  const { sessionId: sync } = await send('Target.attachToTarget', { targetId: observer.stdout.match(/targets=(\S+)/)[1], flatten: true });
  const saved = () => evaluate(sync, `(async () => {
    const { getAllNodes, requestDataAndRegisterForUpdates } = await import('./chrome_sync.js');
    requestDataAndRegisterForUpdates();
    const types = await new Promise(getAllNodes);
    if (!types.some(t => t.type === 'Saved Tab Group')) return null;
    return types.filter(t => t.type === 'Saved Tab Group').flatMap(t => t.nodes)
      .some(n => !n.metadata?.is_deleted && n.SPECIFICS?.saved_tab_group?.group?.title === ${JSON.stringify(name)});
  })()`);
  const { stdout } = await run(process.execPath, [script, name, 'https://example.com/#one', 'https://example.com/#two', '--port', port]);
  windowId = Number(stdout.match(/window=(\d+)/)[1]);
  const tabIds = stdout.match(/tabs=([\d,]+)/)[1].split(',').map(Number);
  await evaluate(extension, `globalThis.ungrouped = [];
    chrome.tabs.onUpdated.addListener((id, change) => {
      if (change.groupId === -1) globalThis.ungrouped.push(id);
    });`);
  await evaluate(extension, `chrome.tabs.create({windowId:${windowId},url:'about:blank',active:false})`);
  for (let i = 0; i < 50 && await saved() === false; i++) await new Promise(resolve => setTimeout(resolve, 100));
  const savedBefore = await saved();
  if (savedBefore !== null) assert.equal(savedBefore, true, 'Test must exercise an automatically saved group');
  const closed = await run(process.execPath, [script, name, '--close', '--port', port]);
  assert.match(closed.stdout, /closed=true/);
  const ungrouped = await evaluate(extension, 'globalThis.ungrouped');
  assert.ok(tabIds.every(id => ungrouped.includes(id)), 'Group must be dissolved before its window is closed');
  if (savedBefore !== null) assert.equal(await saved(), false, `Saved group survived --close: ${name}`);
  let after;
  for (let i = 0; i < 50; i++) {
    after = await evaluate(extension, 'chrome.windows.getAll().then(w => w.map(x => x.id))');
    if (!after.includes(windowId)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(!after.includes(windowId), 'Session window and stray tab must be closed');
  assert.ok(after.includes(observerWindow), 'Unrelated session window must stay open');
  const again = await run(process.execPath, [script, name, '--close', '--port', port]);
  assert.match(again.stdout, /closed=false/);
  console.log(`${version.Browser}: group dissolved, session tabs and stray removed; unrelated windows preserved; repeat close is harmless`);
  console.log(savedBefore === null ? 'Saved-group sync inspection unavailable in this profile' : 'Saved group deletion verified');
} finally {
  for (const ownedWindow of [windowId, observerWindow].filter(Boolean)) if (extension) await evaluate(extension, `(async () => {
    const tabs = await chrome.tabs.query({windowId:${ownedWindow}});
    const grouped = tabs.filter(t => t.groupId !== -1).map(t => t.id);
    if (grouped.length) await chrome.tabs.ungroup(grouped);
    if (tabs.length) await chrome.windows.remove(${ownedWindow});
  })()`).catch(() => {});
  for (const targetId of targets) await send('Target.closeTarget', { targetId });
  ws.close();
}
