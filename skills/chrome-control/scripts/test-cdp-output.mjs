// Smoke check: node test-cdp-output.mjs <port> <targetId>
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
const [port, target] = process.argv.slice(2);
assert.ok(port && target, 'Provide a running test page port and target ID');
const r = spawnSync(process.execPath, [new URL('./cdp-eval.mjs', import.meta.url).pathname,
  port, '"x".repeat(1048576)', '--target', target], { maxBuffer: 2 * 1048576 });
assert.equal(r.status, 0, r.stderr.toString());
assert.equal(r.stdout.length, 1048576, 'Drain stdout before exiting');
const input = spawnSync(process.execPath, [new URL('./cdp-eval.mjs', import.meta.url).pathname,
  port, '-', '--target', target], { input: '"stdin expression"', encoding: 'utf8' });
assert.equal(input.status, 0, input.stderr);
assert.equal(input.stdout, 'stdin expression');
console.log('Large CDP output is complete');
