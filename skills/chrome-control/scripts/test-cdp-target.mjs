// Run: node test-cdp-target.mjs
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';

let wrongTarget = false;
const server = createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify([{id: 'other', type: 'page', url: 'https://example.com',
    webSocketDebuggerUrl: `ws://127.0.0.1:${server.address().port}/other`} ]));
});
server.on('upgrade', (req, socket) => { wrongTarget = true; socket.destroy(); });
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  const child = spawn(process.execPath, [new URL('./cdp-eval.mjs', import.meta.url).pathname,
    String(server.address().port), 'document.title', '--target', 'missing']);
  let stderr = '';
  child.stderr.on('data', b => { stderr += b; });
  const code = await new Promise(resolve => child.on('exit', resolve));
  assert.notEqual(code, 0);
  assert.equal(wrongTarget, false, 'An explicit missing target must never attach to another page');
  assert.match(stderr, /target not found/);
  console.log('Missing-target isolation passed');
} finally { server.close(); }
