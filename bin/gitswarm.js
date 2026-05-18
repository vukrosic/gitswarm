#!/usr/bin/env node
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { basename, dirname, join, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const dashboardScript = join(here, '..', 'dashboard.py');
const GH_BIN = process.env.GITSWARM_GH_BIN || process.env.GH_BIN || 'gh';

const argv = process.argv.slice(2);
const parsed = parseArgs(argv);

if (parsed.command === 'help' || parsed.command === '--help' || parsed.command === '-h') {
  printHelp();
  process.exit(0);
}

if (parsed.command === 'init') {
  try {
    initRepo(parsed.repo);
  } catch (err) {
    console.error(`gitswarm init: ${err.message}`);
    process.exit(1);
  }
  process.exit(0);
}

if (parsed.command === 'doctor') {
  const code = doctorRepo(parsed.repo);
  process.exit(code);
}

if (parsed.command === 'launch' || parsed.command === 'prompt') {
  try {
    const code = await launchPromptSession(parsed.repo, parsed.forwarded);
    process.exit(code);
  } catch (err) {
    console.error(`gitswarm ${parsed.command}: ${err.message}`);
    process.exit(1);
  }
}

launchDashboard(parsed.repo, parsed.forwarded);

function parseArgs(args) {
  let repo = process.env.GITSWARM_REPO || process.cwd();
  let repoFromFlag = false;
  const filtered = [];

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--repo' && args[i + 1]) {
      repo = args[i + 1];
      repoFromFlag = true;
      i += 1;
      continue;
    }
    if (arg.startsWith('--repo=')) {
      repo = arg.slice('--repo='.length);
      repoFromFlag = true;
      continue;
    }
    if (arg === '-C' && args[i + 1]) {
      repo = args[i + 1];
      repoFromFlag = true;
      i += 1;
      continue;
    }
    if (arg.startsWith('-C=')) {
      repo = arg.slice('-C='.length);
      repoFromFlag = true;
      continue;
    }
    filtered.push(arg);
  }

  const command = filtered[0] && isCommand(filtered[0]) ? filtered[0] : 'dashboard';
  const forwarded = command === 'dashboard' ? filtered : filtered.slice(1);
  let repoArg = repo;

  if (!repoFromFlag && (command === 'init' || command === 'doctor') && forwarded[0] && !forwarded[0].startsWith('-')) {
    repoArg = forwarded.shift();
  }

  return { repo: resolve(repoArg), command, forwarded };
}

function isCommand(arg) {
  return ['dashboard', 'init', 'doctor', 'launch', 'prompt', 'help', '--help', '-h'].includes(arg);
}

function printHelp() {
  console.log(`gitswarm

Usage:
  gitswarm [--repo PATH] [dashboard [PORT]]
  gitswarm init [--repo PATH]
  gitswarm doctor [--repo PATH]
  gitswarm launch [options] "prompt text"

Commands:
  dashboard   launch the localhost dashboard (default)
  init        write .gitswarm/config.json and local scaffolding
  doctor      check git + gh + repo connectivity
  launch      launch a fresh agent PTY with a prompt and leave it running
  prompt      alias for launch

Examples:
  gitswarm --repo /path/to/repo
  gitswarm init --repo /path/to/repo
  gitswarm doctor --repo /path/to/repo
  gitswarm launch --agent codex --model gpt-5.4-mini "summarize the first 5 open issues"
  gitswarm launch --issue 14 "tell me what to do next"`);
}

function runGit(repoRoot, args, allowFail = false) {
  const result = spawnSync('git', ['-C', repoRoot, ...args], {
    encoding: 'utf8',
  });
  if (result.status !== 0 && !allowFail) {
    const stderr = (result.stderr || result.stdout || '').trim();
    throw new Error(stderr || `git ${args.join(' ')} failed`);
  }
  return result;
}

function readJson(file) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function configPath(repoRoot) {
  return join(repoRoot, '.gitswarm', 'config.json');
}

function loadConfig(repoRoot) {
  const file = configPath(repoRoot);
  return existsSync(file) ? readJson(file) : null;
}

function writeConfig(repoRoot, config) {
  const dir = join(repoRoot, '.gitswarm');
  mkdirSync(join(dir, 'state'), { recursive: true });
  mkdirSync(join(repoRoot, '.agent-worktrees'), { recursive: true });
  writeFileSync(configPath(repoRoot), `${JSON.stringify(config, null, 2)}\n`);
}

function detectGithubRemote(repoRoot) {
  const remote = runGit(repoRoot, ['remote', 'get-url', 'origin'], true);
  if (remote.status !== 0) return null;
  const url = (remote.stdout || '').trim();
  if (!url) return null;
  const match = url.match(/github\.com[:/](.+?)(?:\.git)?$/);
  return match ? { url, slug: match[1] } : { url, slug: null };
}

function initRepo(repoRoot) {
  const top = resolveRepoRoot(repoRoot);
  const github = detectGithubRemote(top);
  const config = {
    version: 1,
    repo_root: top,
    repo_name: basename(top),
    dashboard_port: 7777,
    state_dir: '.gitswarm/state',
    worktree_dir: '.agent-worktrees',
    created_at: new Date().toISOString(),
  };
  if (github) {
    config.github = github;
  }
  writeConfig(top, config);
  console.log(`gitswarm init: wrote ${configPath(top)}`);
  if (github?.slug) console.log(`gitswarm init: github repo ${github.slug}`);
  console.log(`gitswarm init: next -> gitswarm --repo ${top}`);
}

function doctorRepo(repoRoot) {
  let ok = true;
  const top = resolveRepoRoot(repoRoot);
  const config = loadConfig(top);
  const configNote = config ? `present (${configPath(top)})` : 'missing';
  console.log(`repo: ${top}`);
  console.log(`config: ${configNote}`);
  if (!config) {
    console.log('warning: run `gitswarm init` to create repo defaults');
  }

  const auth = spawnSync(GH_BIN, ['auth', 'status'], {
    cwd: top,
    encoding: 'utf8',
  });
  if (auth.status === 0) {
    console.log('gh auth: ok');
  } else {
    ok = false;
    console.log(`gh auth: failed (${(auth.stderr || auth.stdout || '').trim() || 'unknown error'})`);
  }

  const repoView = spawnSync(GH_BIN, ['repo', 'view', '--json', 'nameWithOwner,url,defaultBranchRef'], {
    cwd: top,
    encoding: 'utf8',
  });
  if (repoView.status === 0) {
    try {
      const parsed = JSON.parse(repoView.stdout || '{}');
      console.log(`gh repo: ${parsed.nameWithOwner || 'unknown'}${parsed.defaultBranchRef?.name ? ` · default ${parsed.defaultBranchRef.name}` : ''}`);
    } catch {
      ok = false;
      console.log('gh repo: failed to parse response');
    }
  } else {
    ok = false;
    console.log(`gh repo: failed (${(repoView.stderr || repoView.stdout || '').trim() || 'unknown error'})`);
  }

  const issues = spawnSync(GH_BIN, ['issue', 'list', '--state', 'open', '--limit', '1', '--json', 'number'], {
    cwd: top,
    encoding: 'utf8',
  });
  if (issues.status === 0) {
    try {
      const parsed = JSON.parse(issues.stdout || '[]');
      console.log(`gh issues: ok (${parsed.length} sample row${parsed.length === 1 ? '' : 's'})`);
    } catch {
      ok = false;
      console.log('gh issues: failed to parse response');
    }
  } else {
    ok = false;
    console.log(`gh issues: failed (${(issues.stderr || issues.stdout || '').trim() || 'unknown error'})`);
  }

  const prs = spawnSync(GH_BIN, ['pr', 'list', '--limit', '1', '--json', 'number'], {
    cwd: top,
    encoding: 'utf8',
  });
  if (prs.status === 0) {
    try {
      const parsed = JSON.parse(prs.stdout || '[]');
      console.log(`gh prs: ok (${parsed.length} sample row${parsed.length === 1 ? '' : 's'})`);
    } catch {
      ok = false;
      console.log('gh prs: failed to parse response');
    }
  } else {
    ok = false;
    console.log(`gh prs: failed (${(prs.stderr || prs.stdout || '').trim() || 'unknown error'})`);
  }

  const stateDir = join(top, '.gitswarm', 'state');
  const worktreeDir = join(top, '.agent-worktrees');
  try {
    mkdirSync(stateDir, { recursive: true });
    mkdirSync(worktreeDir, { recursive: true });
    console.log('local dirs: ok');
  } catch (err) {
    ok = false;
    console.log(`local dirs: failed (${err.message})`);
  }

  return ok ? 0 : 1;
}

function resolveRepoRoot(repoPath) {
  const top = runGit(resolve(repoPath), ['rev-parse', '--show-toplevel']);
  return resolve((top.stdout || '').trim());
}

function launchDashboard(repoRoot, forwarded) {
  const config = loadConfig(repoRoot);
  const args = forwarded.length ? forwarded : [String(config?.dashboard_port || 7777)];
  const child = spawn('python3', [dashboardScript, ...args], {
    stdio: 'inherit',
    env: process.env,
    cwd: repoRoot,
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
}

function parseLaunchArgs(args) {
  let agent = process.env.GITSWARM_AGENT || 'codex';
  let model = '';
  let cwd = '';
  let port = '';
  let label = '';
  let issue = '';
  let prompt = '';

  const rest = [];
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '--agent' && args[i + 1]) { agent = args[++i]; continue; }
    if (arg.startsWith('--agent=')) { agent = arg.slice('--agent='.length); continue; }
    if (arg === '--model' && args[i + 1]) { model = args[++i]; continue; }
    if (arg.startsWith('--model=')) { model = arg.slice('--model='.length); continue; }
    if (arg === '--cwd' && args[i + 1]) { cwd = args[++i]; continue; }
    if (arg.startsWith('--cwd=')) { cwd = arg.slice('--cwd='.length); continue; }
    if (arg === '--port' && args[i + 1]) { port = args[++i]; continue; }
    if (arg.startsWith('--port=')) { port = arg.slice('--port='.length); continue; }
    if (arg === '--label' && args[i + 1]) { label = args[++i]; continue; }
    if (arg.startsWith('--label=')) { label = arg.slice('--label='.length); continue; }
    if (arg === '--issue' && args[i + 1]) { issue = args[++i]; continue; }
    if (arg.startsWith('--issue=')) { issue = arg.slice('--issue='.length); continue; }
    if (arg === '--') {
      rest.push(...args.slice(i + 1));
      break;
    }
    rest.push(arg);
  }
  prompt = rest.join(' ').trim();
  return { agent, model, cwd, port, label, issue, prompt };
}

async function ensureDashboardRunning(repoRoot, port) {
  const config = loadConfig(repoRoot);
  const resolvedPort = String(port || config?.dashboard_port || 7777);
  const url = `http://127.0.0.1:${resolvedPort}`;
  try {
    const res = await fetch(`${url}/api/agents`, { method: 'GET' });
    if (res.ok) return resolvedPort;
  } catch {
    // fall through and start a background dashboard
  }

  const logDir = join(repoRoot, '.gitswarm');
  mkdirSync(logDir, { recursive: true });
  const child = spawn('python3', [dashboardScript, resolvedPort], {
    cwd: repoRoot,
    detached: true,
    stdio: 'ignore',
    env: process.env,
  });
  child.unref();

  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const res = await fetch(`${url}/api/agents`, { method: 'GET' });
      if (res.ok) return resolvedPort;
    } catch {
      // retry
    }
    await new Promise((rs) => setTimeout(rs, 200));
  }
  throw new Error(`dashboard did not start on ${url}`);
}

async function launchPromptSession(repoRoot, forwarded) {
  const opts = parseLaunchArgs(forwarded);
  if (!opts.prompt) {
    throw new Error('usage: gitswarm launch [--agent codex] [--model MODEL] [--cwd PATH] [--port PORT] "prompt text"');
  }

  const port = await ensureDashboardRunning(repoRoot, opts.port);
  const url = `http://127.0.0.1:${port}`;
  const body = {
    kind: 'agent-prompt',
    agent: opts.agent,
    model: opts.model || undefined,
    cwd: opts.cwd || undefined,
    issue: opts.issue ? Number(opts.issue) : undefined,
    label: opts.label || opts.prompt,
    prompt: opts.prompt,
    rows: 30,
    cols: 120,
  };
  const res = await fetch(`${url}/api/pty/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) {
    throw new Error(data.error || `launch failed (${res.status})`);
  }
  console.log(`gitswarm launch: started ${data.agent || opts.agent} · ${data.label || data.sid}`);
  console.log(`gitswarm launch: dashboard ${url}`);
  console.log(`gitswarm launch: sid ${data.sid}`);
  return 0;
}
