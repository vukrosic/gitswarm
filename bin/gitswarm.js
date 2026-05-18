#!/usr/bin/env node
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { existsSync } from 'node:fs';

const here = dirname(fileURLToPath(import.meta.url));
const script = join(here, '..', 'dashboard.py');
const argv = process.argv.slice(2);
let repo = process.env.GITSWARM_REPO || process.cwd();
const forwarded = [];

for (let i = 0; i < argv.length; i += 1) {
  const arg = argv[i];
  if (arg === '--repo' && argv[i + 1]) {
    repo = argv[i + 1];
    i += 1;
    continue;
  }
  if (arg.startsWith('--repo=')) {
    repo = arg.slice('--repo='.length);
    continue;
  }
  if (arg === '-C' && argv[i + 1]) {
    repo = argv[i + 1];
    i += 1;
    continue;
  }
  if (arg.startsWith('-C=')) {
    repo = arg.slice('-C='.length);
    continue;
  }
  forwarded.push(arg);
}

const cwd = resolve(repo);
if (!existsSync(cwd)) {
  console.error(`gitswarm: repo path does not exist: ${cwd}`);
  process.exit(1);
}

const child = spawn('python3', [script, ...forwarded], {
  stdio: 'inherit',
  env: process.env,
  cwd,
});

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => {
    if (!child.killed) child.kill(sig);
  });
}

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 1);
});
