INDEX_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>gitswarm</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.min.css">
<script src="https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@xterm/addon-web-links@0.11.0/lib/addon-web-links.min.js"></script>
<style>
body{font:14px/1.5 ui-monospace,Menlo,Consolas,monospace;margin:0;background:#0d1117;color:#c9d1d9;height:100vh;overflow:hidden;}
header{padding:12px 18px;border-bottom:1px solid #30363d;background:#161b22;display:flex;gap:18px;align-items:center;flex-wrap:wrap;}
header h1{margin:0;font-size:15px;color:#f0f6fc;font-weight:600;}
header span{color:#8b949e;font-size:12px;}
header button{background:#1f6feb;color:#fff;border:1px solid #1f6feb;border-radius:5px;padding:5px 12px;cursor:pointer;font-size:12px;font-family:inherit;}
header button:hover{background:#2f7fff;}
main{display:grid;grid-template-columns:340px 1fr;height:calc(100vh - 50px);}
aside{border-right:1px solid #30363d;overflow-y:auto;background:#0d1117;}
aside h2{font-size:11px;text-transform:uppercase;color:#8b949e;letter-spacing:0.08em;margin:14px 18px 6px;display:flex;justify-content:space-between;align-items:center;}
aside h2 .count{color:#6e7681;font-weight:normal;text-transform:none;letter-spacing:0;}
aside .file{padding:6px 18px;cursor:pointer;border-left:3px solid transparent;font-size:13px;}
aside .file:hover{background:#161b22;}
aside .file.active{background:#161b22;border-left-color:#1f6feb;color:#58a6ff;}
aside .meta{font-size:11px;color:#6e7681;margin-left:8px;}
section{display:flex;flex-direction:column;overflow:hidden;background:#000;}
section h2{margin:0;padding:10px 18px;border-bottom:1px solid #30363d;font-size:13px;background:#0d1117;display:flex;justify-content:space-between;align-items:center;}
section h2 .ctl{font-size:11px;color:#8b949e;font-weight:400;}
section h2 button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:5px;padding:3px 8px;cursor:pointer;font-size:11px;margin-left:6px;}
section h2 button.on{background:#1f6feb;color:#fff;border-color:#1f6feb;}
#term-wrap{flex:1;padding:8px;overflow:hidden;background:#000;}
.xterm{height:100%;}
#hint{padding:40px;color:#6e7681;text-align:center;background:#000;}
.empty{padding:40px 18px;color:#6e7681;text-align:center;}
.worktree{padding:8px 18px;font-size:12px;border-bottom:1px solid #21262d;}
.worktree .name{color:#58a6ff;}
.worktree .commits{color:#8b949e;font-size:11px;margin-top:2px;}
.worktree.live .name::before{content:"● ";color:#3fb950;animation:pulse 1.2s infinite;}
.worktree button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px;font-family:inherit;margin-top:4px;}
.worktree button:hover{background:#1f6feb;color:#fff;border-color:#1f6feb;}
@keyframes pulse{50%{opacity:0.4;}}
.pty{padding:8px 18px;font-size:12px;border-bottom:1px solid #21262d;cursor:pointer;border-left:3px solid transparent;}
.pty:hover{background:#161b22;}
.pty.active{background:#161b22;border-left-color:#3fb950;}
.pty .meta{font-size:10px;color:#6e7681;margin-top:2px;word-break:break-all;}
.filters{padding:0 18px 8px;display:flex;gap:4px;flex-wrap:wrap;}
.filters button{background:#0d1117;color:#8b949e;border:1px solid #30363d;border-radius:12px;padding:3px 10px;cursor:pointer;font-size:11px;font-family:inherit;}
.filters button:hover{color:#c9d1d9;}
.filters button.on{background:#1f6feb;color:#fff;border-color:#1f6feb;}
.issue,.pr{padding:10px 18px;border-bottom:1px solid #21262d;font-size:12px;}
.issue .num,.pr .num{color:#8b949e;}
.issue .ttl,.pr .ttl{color:#c9d1d9;margin-bottom:6px;display:flex;align-items:baseline;gap:6px;}
.issue .ttl .caret{cursor:pointer;color:#6e7681;font-size:10px;width:10px;flex-shrink:0;user-select:none;}
.issue .ttl .caret:hover{color:#58a6ff;}
.issue .ttl .title-text{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.issue .ttl .ext{color:#6e7681;text-decoration:none;font-size:11px;opacity:0;transition:opacity 0.1s;flex-shrink:0;}
.issue:hover .ttl .ext{opacity:1;}
.issue .ttl .ext:hover{color:#58a6ff;}
.issue.open .ttl .title-text{white-space:normal;}
.issue .summary,.pr .summary{margin:4px 0 6px;color:#8b949e;font-size:11px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.issue .meta,.pr .meta,.session .meta,.activity-item .meta{font-size:10px;color:#6e7681;margin-bottom:6px;}
.issue .suggested,.pr .checks,.session .status,.activity-item .meta-line{font-size:10px;color:#6e7681;margin-bottom:6px;}
.issue .suggested .lbl{background:#16233a;color:#79c0ff;}
.issue .body{display:none;margin:6px 0 8px 16px;padding:8px 10px;background:#0d1117;border-left:2px solid #30363d;border-radius:0 3px 3px 0;font-size:11px;color:#c9d1d9;line-height:1.5;max-height:340px;overflow-y:auto;}
.issue.open .body{display:block;}
.issue .body pre{background:#161b22;padding:6px 8px;border-radius:3px;overflow-x:auto;font-size:10px;margin:4px 0;}
.issue .body code{background:#161b22;padding:0 4px;border-radius:2px;font-size:10px;}
.issue .body pre code{background:transparent;padding:0;}
.issue .body b{color:#58a6ff;display:block;margin-top:6px;}
.issue .body a{color:#58a6ff;}
.issue .body-loading,.issue .body-err{color:#6e7681;font-style:italic;padding:4px 0;}
.issue .body-err{color:#ff7b72;}
.issue.busy .ttl::before{content:"⏳ ";color:#d29922;}
.issue.parked .ttl{color:#6e7681;}
.issue .lbls,.pr .lbls{font-size:10px;color:#6e7681;margin-bottom:6px;}
.issue .lbls .lbl,.pr .lbls .lbl{display:inline-block;background:#161b22;padding:1px 6px;border-radius:8px;margin-right:3px;color:#8b949e;}
.issue .lbls .lbl.claim-next{background:#0e3a1a;color:#3fb950;}
.issue .lbls .lbl.in-progress{background:#3a2f0e;color:#d29922;}
.issue .lbls .lbl.needs-validation{background:#222;color:#6e7681;}
.issue .lbls .lbl.keystone{background:#4a0f2a;color:#f778ba;}
.issue .row,.pr .row{display:flex;gap:6px;flex-wrap:wrap;}
.issue button,.pr button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:5px;padding:4px 8px;cursor:pointer;font-size:11px;font-family:inherit;flex:1;}
.issue button:hover:not(:disabled),.pr button:hover:not(:disabled){background:#1f6feb;color:#fff;border-color:#1f6feb;}
.issue button:disabled,.pr button:disabled{opacity:0.4;cursor:not-allowed;}
.issue button.headless{background:#0d1117;}
.pr .badges{font-size:10px;color:#6e7681;margin-bottom:6px;}
.pr .badges .b{display:inline-block;padding:1px 6px;border-radius:3px;margin-right:4px;background:#161b22;}
.pr .badges .b.draft{color:#8b949e;}
.pr .badges .b.approved{background:#0e3a1a;color:#3fb950;}
.pr .badges .b.changes_requested{background:#4a0e0e;color:#ff7b72;}
.pr .badges .b.ci-pass{background:#0e3a1a;color:#3fb950;}
.pr .badges .b.ci-fail{background:#4a0e0e;color:#ff7b72;}
.pr .badges .b.ci-pending{background:#3a2f0e;color:#d29922;}
.pr .badges .b.ready{background:#0e3a1a;color:#56d364;}
.pr .checks .fail{color:#ff7b72;}
.pr .checks .pending{color:#d29922;}
.pr button.merge{background:#1a3a1a;color:#56d364;border-color:#234a23;}
.pr button.merge:hover:not(:disabled){background:#0e6e0e;color:#fff;border-color:#0e6e0e;}
.pr button.review{background:#1a1a3a;color:#79c0ff;border-color:#23234a;}
.pr button.review:hover:not(:disabled){background:#0e2e6e;color:#fff;border-color:#0e2e6e;}
.pr button.review.done{background:#161b22;color:#6e7681;border-color:#21262d;}
.pr button.review.done:hover:not(:disabled){background:#21262d;color:#8b949e;border-color:#30363d;}
.pr button.merge.interactive{background:#1a3a2a;color:#56d364;border-color:#234a32;}
.pr button.merge.interactive:hover:not(:disabled){background:#0e6e3e;color:#fff;border-color:#0e6e3e;}
.pr button.fixci{background:#3a251a;color:#f2cc60;border-color:#5a3826;}
.pr button.fixci:hover:not(:disabled){background:#7a4d2f;color:#fff;border-color:#7a4d2f;}
.pr a.reviewed{display:inline-block;margin-left:6px;padding:0 5px;border-radius:8px;background:#21262d;color:#7d8590;font-size:10px;text-decoration:none;border:1px solid #30363d;vertical-align:1px;}
.pr a.reviewed:hover{background:#2d333b;color:#c9d1d9;border-color:#58a6ff;}
aside .session{padding:8px 18px;font-size:12px;border-bottom:1px solid #21262d;}
aside .session .title{display:flex;justify-content:space-between;gap:8px;align-items:baseline;color:#c9d1d9;}
aside .session .title .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
aside .session .idle{color:#d29922;font-size:10px;flex-shrink:0;}
aside .session .meta-line{font-size:10px;color:#6e7681;margin-top:2px;word-break:break-all;}
aside .session button{background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px;font-family:inherit;margin-top:4px;}
aside .session button:hover{background:#1f6feb;color:#fff;border-color:#1f6feb;}
aside .activity-item{padding:8px 18px;font-size:12px;border-bottom:1px solid #21262d;}
aside .activity-item .head{display:flex;justify-content:space-between;gap:8px;align-items:baseline;}
aside .activity-item .kind{font-size:10px;color:#6e7681;text-transform:uppercase;letter-spacing:0.08em;flex-shrink:0;}
aside .activity-item .title{color:#c9d1d9;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
aside .activity-item .meta-line{font-size:10px;color:#6e7681;margin-top:2px;}
aside h2 .hdr-btn{float:right;background:#0d1117;color:#8b949e;border:1px solid #30363d;border-radius:4px;padding:2px 8px;font-size:11px;font-family:inherit;cursor:pointer;margin-left:6px;font-weight:normal;}
aside h2 .hdr-btn:hover{color:#c9d1d9;border-color:#58a6ff;}
#pr-bar{padding:6px 12px;background:#0d1117;border-bottom:1px solid #21262d;font-size:11px;color:#8b949e;display:none;}
#pr-bar.show{display:block;}
#pr-bar a{color:#58a6ff;text-decoration:none;}
#pr-bar a:hover{text-decoration:underline;}
#pr-bar .sep{color:#30363d;margin:0 8px;}
#pr-bar .verdict-link{color:#56d364;}
#toast{position:fixed;bottom:20px;right:20px;background:#161b22;color:#c9d1d9;padding:10px 16px;border-radius:6px;border:1px solid #30363d;font-size:12px;display:none;z-index:100;}
#toast.err{border-color:#f85149;color:#ff7b72;}
#toast.ok{border-color:#3fb950;color:#56d364;}
#tip{position:fixed;background:#1f2428;color:#f0f6fc;padding:6px 10px;border-radius:5px;font-size:11px;font-family:ui-monospace,Menlo,Consolas,monospace;border:1px solid #30363d;pointer-events:none;display:none;z-index:10000;max-width:320px;white-space:normal;line-height:1.4;box-shadow:0 4px 14px rgba(0,0,0,0.5);opacity:0;transition:opacity 0.12s ease;}
#tip.show{opacity:1;}
</style></head>
<body>
<header>
  <h1>gitswarm</h1>
  <button id="newShellBtn" title="Open an interactive bash shell in the repo root (no agent)">+ new shell</button>
  <button id="newAgentBtn" title="Open the selected CLI agent interactively in the repo root (no prompt)">💬 new agent</button>
  <label style="font-size:12px;color:#8b949e;display:flex;align-items:center;gap:6px;">
    agent
    <select id="agentSelect" title="Which CLI agent to launch for + new agent / claim / review / merge / fix-ci / propose. Saved to localStorage."
            style="background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:5px;padding:4px 6px;font:inherit;font-size:12px;cursor:pointer;">
      <option value="codex">codex</option>
    </select>
  </label>
  <span id="lastUpdate">—</span>
  <span>Live terminals stream via long-poll · Log files refresh every 800ms when followed</span>
</header>
<main>
  <aside>
    <h2>Issues <span class="count" id="issueCount"></span>
      <button class="hdr-btn" onclick="proposeIssue()" title="Open the selected agent interactively and draft a new issue body (scenario, demo, acceptance, anti-features, files). When the agent exits, the shell stays open with a ready-to-run gh issue create command.">📝 propose</button>
      <button class="hdr-btn" onclick="batchClaimNext()" title="Launch the next few claim-next issues as issue shells, one after another, so you can fan out work fast.">↧ batch</button>
    </h2>
    <div class="filters" id="filters">
      <button data-f="all" class="on" title="All open issues, including validated, in-progress, and parked ones.">all</button>
      <button data-f="claim-next" title="Issues open for an agent to grab. The orchestrator picks the lowest-numbered one by default.">claim-next</button>
      <button data-f="good first issue" title="Triaged as approachable for a new contributor or new agent.">good first</button>
      <button data-f="agent-friendly" title="Self-contained scope that fits the agent contract (single file, demo, anti-features).">agent</button>
      <button data-f="needs-validation" title="Speculative — waiting on a real user to confirm before opening for agents.">parked</button>
    </div>
    <div id="issues"><div class="empty">loading…</div></div>
    <h2>Open PRs <span class="count" id="prCount"></span></h2>
    <div id="prs"><div class="empty">loading…</div></div>
    <h2>Needs me <span class="count" id="needsCount"></span></h2>
    <div id="needsme"><div class="empty">waiting for an idle agent session…</div></div>
    <h2>Live terminals</h2>
    <div id="ptys"><div class="empty">no terminals · click + new shell</div></div>
    <h2>Active worktrees <span class="count" id="worktreeCount"></span>
      <button class="hdr-btn" onclick="pruneMergedWorktrees()" title="Remove any clean merged worktrees while keeping the branches for later restoration.">🧹 prune merged</button>
    </h2>
    <div id="worktrees"><div class="empty">none</div></div>
    <h2>Activity <span class="count" id="activityCount"></span></h2>
    <div id="activity"><div class="empty">nothing recent yet</div></div>
    <h2>State files
      <button class="hdr-btn" onclick="cleanupState(true)" title="Dry-run: list state files older than 7 days that the cleanup would remove. Nothing is deleted.">🧹 audit</button>
      <button class="hdr-btn" onclick="cleanupState(false)" title="Delete state files older than 7 days (implementer/orchestrator logs, prompts, diffs, drafts). Worktrees and the .gitignore are never touched.">🧹 prune</button>
    </h2>
    <div id="files"><div class="empty">scanning…</div></div>
  </aside>
  <div id="toast"></div>
  <div id="tip"></div>
  <section>
    <h2><span id="title">pick a file or open a shell →</span>
      <span class="ctl">
        <button id="followBtn" title="Jump to the bottom of the buffer (xterm auto-tails once you're there)">↓ bottom</button>
        <button id="replayBtn" title="Re-play a completed log from byte zero with a typing animation (file mode only).">replay</button>
        <button id="clearBtn" title="Clear the terminal pane. Doesn't kill the session; output keeps streaming.">clear</button>
        <button id="killBtn" title="Kill the current PTY session">close ✕</button>
      </span>
    </h2>
    <div id="pr-bar"></div>
    <div id="term-wrap"><div id="hint">Pick an <b>agent</b> in the header (codex / claude / minimax) — it routes the buttons below.<br>🖥️ <b>⚑ claim</b> next to an issue: preps a fresh worktree and launches the agent interactively with the issue's prompt loaded.<br>🔍 <b>review</b> next to a PR: same interactive mode, with the PR diff + linked issue body pre-loaded as the review prompt. Verdict auto-posts to the PR when the agent exits.<br>🟢 <b>merge</b> next to a PR: opens an agent session that runs <code>gh pr merge --squash --delete-branch</code> and handles conflicts.<br>🩹 <b>fix CI</b> next to a PR: opens an agent session inside the PR worktree to address failing checks.<br>📝 <b>propose</b> in the Issues header: drafts a new issue body interactively.<br>💬 <b>new agent</b> in header: free-form agent REPL in the repo root, no prompt.<br>💻 <b>+ new shell</b> in header: plain bash in the repo root.<br>📁 Click any state file on the left to tail an agent's log.<br>🧹 <b>State files</b> header: <i>audit</i> shows what's old, <i>prune</i> deletes it.</div></div>
  </section>
</main>
<script>
const term = new Terminal({
  fontFamily: 'ui-monospace, Menlo, Consolas, monospace',
  fontSize: 13,
  lineHeight: 1.25,
  theme: {
    background: '#000000', foreground: '#c9d1d9', cursor: '#58a6ff',
    black:'#484f58', red:'#ff7b72', green:'#3fb950', yellow:'#d29922',
    blue:'#58a6ff', magenta:'#bc8cff', cyan:'#39c5cf', white:'#b1bac4',
    brightBlack:'#6e7681', brightRed:'#ffa198', brightGreen:'#56d364', brightYellow:'#e3b341',
    brightBlue:'#79c0ff', brightMagenta:'#d2a8ff', brightCyan:'#56d4dd', brightWhite:'#f0f6fc'
  },
  convertEol: false, scrollback: 50000, cursorBlink: true
});
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);
term.loadAddon(new WebLinksAddon.WebLinksAddon());

let termAttached = false;
let inputHandler = null;
function attachTerm() {
  if (termAttached) return;
  const wrap = document.getElementById('term-wrap');
  wrap.innerHTML = '';
  term.open(wrap);
  fitAddon.fit();
  termAttached = true;
  window.addEventListener('resize', () => { try { fitAddon.fit(); sendResize(); } catch(e){} });
  // One single onData handler; it dispatches based on the current mode.
  term.onData(data => { if (inputHandler) inputHandler(data); });
}

// Current view state. Either {kind:'file', name} or {kind:'pty', sid, label}.
let view = null;
let cursor = 0;        // bytes already written / offset acknowledged
let follow = true;
let pollTimer = null;
let replayMode = false;
let ptyAbort = null;
let ptyStreamGen = 0;  // bumped on every selectPty to abort stale loops
let allPtys = [];
let allWorktrees = [];
let allPRs = [];
let idleState = new Map();   // sid -> {lastOutput, notified}

function sendResize() {
  if (!view || view.kind !== 'pty' || !termAttached) return;
  const rows = term.rows, cols = term.cols;
  fetch('/api/pty/resize', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sid: view.sid, rows, cols})}).catch(()=>{});
}

function fmtSize(n){if(n<1024)return n+'B';if(n<1024*1024)return (n/1024).toFixed(1)+'K';return (n/1048576).toFixed(1)+'M';}
function fmtTime(s){const d=new Date(s*1000);return d.toLocaleTimeString();}
function fmtWhen(ts){ const d = ts ? new Date(ts) : null; return d && !Number.isNaN(d.getTime()) ? d.toLocaleString() : ''; }
function fmtAgo(ts) {
  const d = ts ? new Date(ts) : null;
  if (!d || Number.isNaN(d.getTime())) return '';
  let s = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (s < 60) return s + 's';
  const m = Math.floor(s / 60); if (m < 60) return m + 'm';
  const h = Math.floor(m / 60); if (h < 24) return h + 'h';
  const d2 = Math.floor(h / 24); return d2 + 'd';
}
function fmtIdle(ts) {
  const age = fmtAgo(ts);
  return age ? `idle ${age}` : '';
}

async function listFiles() {
  try {
    const r = await fetch('/api/files');
    const data = await r.json();
    const el = document.getElementById('files');
    if (!data.files.length) { el.innerHTML = '<div class="empty">no logs yet</div>'; }
    else {
      el.innerHTML = data.files.map(f => {
        const cls = (view && view.kind === 'file' && view.name === f.name) ? 'file active' : 'file';
        const safeName = f.name.replace(/'/g, "\\'");
        return `<div class="${cls}" data-name="${f.name}" title="Tail this log file (${fmtSize(f.size)}). Read-only — keystrokes are dropped." onclick="selectFile('${safeName}')">${f.name}<span class="meta">${fmtSize(f.size)} · ${fmtTime(f.mtime)}</span></div>`;
      }).join('');
    }
    document.getElementById('lastUpdate').textContent = 'updated ' + new Date().toLocaleTimeString();
  } catch(e) { console.error(e); }
}

async function listWorktrees() {
  try {
    const r = await fetch('/api/worktrees');
    const data = await r.json();
    const el = document.getElementById('worktrees');
    allWorktrees = data.worktrees || [];
    const mergeCandidates = allWorktrees.filter(w => w.status === 'merge candidate').length;
    document.getElementById('worktreeCount').textContent = `${mergeCandidates} merge candidate${mergeCandidates === 1 ? '' : 's'}`;
    const runningSet = new Set((data.running || []).filter(r => r.active).map(r => r.worktree));
    if (!allWorktrees.length) { el.innerHTML = '<div class="empty">none</div>'; }
    else {
      el.innerHTML = allWorktrees.map(w => {
        const safe = w.name.replace(/'/g, "\\'");
        const status = w.status || (w.dirty ? 'dirty' : 'clean');
        const safeRemove = !!w.safe_remove;
        const statusBadge = status === 'merge candidate'
          ? '<span class="lbl" style="background:#0e3a1a;color:#56d364;">merge candidate</span>'
          : status === 'merged'
          ? '<span class="lbl" style="background:#0d1117;color:#8b949e;">merged</span>'
          : status === 'dirty'
          ? '<span class="lbl" style="background:#4a0e0e;color:#ff7b72;">dirty</span>'
          : '<span class="lbl" style="background:#161b22;color:#8b949e;">clean</span>';
        const removeBtn = safeRemove
          ? `<button onclick="removeWorktree('${safe}')" title="Safely remove this worktree while keeping the branch for later restoration">🧹 prune</button>`
          : '';
        return `<div class="worktree ${runningSet.has(w.name) ? 'live' : ''}"><div class="name">${w.name} ${statusBadge}</div><div class="commits">${w.commits || 'no commits yet'} · ${w.branch || 'no branch'} · ${status}${w.ahead ? ` · +${w.ahead}` : ''}${runningSet.has(w.name) ? ' · agent active' : ''}</div><button onclick="openWorktreeShell('${safe}')" title="Open an interactive shell in this worktree">🖥️ open shell</button>${removeBtn}</div>`;
      }).join('');
    }
  } catch(e) { console.error(e); }
}

async function pruneMergedWorktrees() {
  const targets = allWorktrees.filter(w => w.safe_remove);
  if (!targets.length) { showToast('no merged worktrees to prune', 'err'); return; }
  if (!confirm(`Prune ${targets.length} merged worktree${targets.length === 1 ? '' : 's'}? The branches stay around for later recreation.`)) return;
  for (const w of targets) {
    await removeWorktree(w.name, true);
  }
  await listWorktrees();
}

let issueFilter = 'all';
let allIssues = [];
const _issueBodyCache = new Map();   // num -> body markdown

async function listIssues() {
  try {
    const r = await fetch('/api/issues');
    const data = await r.json();
    if (data.issues && data.issues[0] && data.issues[0].error) {
      document.getElementById('issues').innerHTML = `<div class="empty">gh error: ${data.issues[0].error}</div>`;
      return;
    }
    allIssues = data.issues || [];
    for (const it of allIssues) {
      if (it && it.number != null && it.body) _issueBodyCache.set(String(it.number), it.body);
    }
    const claimable = allIssues.filter(it => it.labels && it.labels.includes('claim-next')).length;
    document.getElementById('issueCount').textContent = `${allIssues.length} open · ${claimable} claim-next`;
    renderIssues();
    renderActivity();
  } catch(e) { console.error(e); }
}

function renderIssues() {
  const el = document.getElementById('issues');
  const filtered = issueFilter === 'all'
    ? allIssues
    : allIssues.filter(it => it.labels.includes(issueFilter));
  if (!filtered.length) { el.innerHTML = `<div class="empty">no issues match "${issueFilter}"</div>`; return; }
  el.innerHTML = filtered.map(it => {
    const interesting = it.labels.filter(l => ['claim-next','in-progress','needs-validation','keystone','good first issue','agent-friendly'].includes(l));
    const labelChips = interesting.map(l => `<span class="lbl ${l.replace(/[^a-z0-9-]/g,'-')}">${l}</span>`).join('');
    const suggested = (it.suggested_labels || []).filter(l => !it.labels.includes(l));
    const suggestedChips = suggested.length ? `<span class="suggested">suggested ${suggested.map(l => `<span class="lbl">${l}</span>`).join('')}</span>` : '';
    const metaBits = [];
    if (it.author) metaBits.push(`by ${it.author}`);
    if (it.assignees && it.assignees.length) metaBits.push(`assignee ${it.assignees.join(', ')}`);
    if (it.updatedAt) metaBits.push(`updated ${fmtAgo(it.updatedAt)} ago`);
    if (it.comment_count != null) metaBits.push(`${it.comment_count} comment${it.comment_count === 1 ? '' : 's'}`);
    const summary = escapeHtml(it.summary || 'no body yet');
    const tooltip = escapeHtml(`${it.title}\n${it.summary || ''}`.trim());
    return `
      <div class="issue ${it.in_progress ? 'busy' : ''} ${it.parked ? 'parked' : ''}" data-num="${it.number}">
        <div class="ttl">
          <span class="caret" data-action="toggle" title="Show issue body (Researcher / Demo / Acceptance / Anti-features / Files)">▸</span>
          <span class="num">#${it.number}</span>
          <span class="title-text" title="${tooltip}">${escapeHtml(it.title)}</span>
          <a class="ext" href="${escapeHtml(it.url)}" target="_blank" title="Open issue on GitHub">↗</a>
        </div>
        <div class="summary">${summary}</div>
        ${metaBits.length ? `<div class="meta">${escapeHtml(metaBits.join(' · '))}</div>` : ''}
        ${labelChips ? `<div class="lbls">${labelChips}</div>` : ''}
        ${suggestedChips ? `<div class="suggested">${suggestedChips}</div>` : ''}
        <div class="body" id="ibody-${it.number}"></div>
        <div class="row">
          <button onclick="launchIssueShell(${it.number})" title="Claim the issue, prep a fresh worktree, and run the selected agent interactively with the issue prompt loaded">⚑ claim</button>
          <button onclick="window.open('${it.url}', '_blank')" title="Open issue on GitHub">↗ GitHub</button>
          <button onclick="launchIssue(${it.number}, 'watch')" ${it.in_progress ? 'disabled' : ''} title="Spawn orchestrator (headless codex exec); auto-switch terminal to log">▶ watch</button>
          <button class="headless" onclick="launchIssue(${it.number}, 'headless')" ${it.in_progress ? 'disabled' : ''} title="Spawn orchestrator in background; don't switch view">⌁ bg</button>
        </div>
      </div>
    `;
  }).join('');
}

// Event delegation for issue caret clicks — toggles the body panel.
document.getElementById('issues').addEventListener('click', async (e) => {
  const c = e.target.closest('.caret');
  if (!c) return;
  const row = c.closest('.issue');
  if (!row) return;
  const num = row.dataset.num;
  const body = document.getElementById('ibody-' + num);
  const open = row.classList.toggle('open');
  c.textContent = open ? '▾' : '▸';
  if (!open) { body.innerHTML = ''; return; }
  if (_issueBodyCache.has(num)) {
    body.innerHTML = renderIssueBody(_issueBodyCache.get(num));
    return;
  }
  body.innerHTML = '<div class="body-loading">loading…</div>';
  try {
    const r = await fetch('/api/issue?num=' + num);
    const d = await r.json();
    if (d.error) { body.innerHTML = `<div class="body-err">${escapeHtml(d.error)}</div>`; return; }
    _issueBodyCache.set(num, d.body || '_(empty body)_');
    body.innerHTML = renderIssueBody(d.body || '_(empty body)_');
  } catch(err) {
    body.innerHTML = `<div class="body-err">fetch failed: ${escapeHtml(String(err))}</div>`;
  }
});

// Tiny markdown — only what we need for issue bodies: headings, code blocks,
// inline code, links, line breaks. Anything else falls through as plain text.
function renderIssueBody(md) {
  let html = escapeHtml(md);
  // ```fenced code```
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, (_, lang, code) => `<pre><code>${code}</code></pre>`);
  // ### / ## / # headings
  html = html.replace(/^###\s+(.+)$/gm, '<b>$1</b>');
  html = html.replace(/^##\s+(.+)$/gm, '<b>$1</b>');
  html = html.replace(/^#\s+(.+)$/gm, '<b>$1</b>');
  // [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  // `inline code`
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');
  // remaining newlines
  html = html.replace(/\n/g, '<br>');
  return html;
}

async function listPRs() {
  try {
    const r = await fetch('/api/prs');
    const data = await r.json();
    const el = document.getElementById('prs');
    if (data.prs && data.prs[0] && data.prs[0].error) {
      el.innerHTML = `<div class="empty">gh error: ${data.prs[0].error}</div>`;
      return;
    }
    allPRs = (data.prs || []).slice().sort((a, b) => {
      const score = pr => {
        const ready = pr.mergeable === 'MERGEABLE' && !pr.isDraft && pr.ci === 'pass' && pr.reviewDecision !== 'CHANGES_REQUESTED';
        if (ready) return 0;
        if (pr.ci === 'fail') return 1;
        if (pr.reviewDecision === 'CHANGES_REQUESTED') return 2;
        if (pr.isDraft) return 3;
        return 4;
      };
      const diff = score(a) - score(b);
      return diff || (a.number - b.number);
    });
    const readyCount = allPRs.filter(pr => pr.mergeable === 'MERGEABLE' && !pr.isDraft && pr.ci === 'pass' && pr.reviewDecision !== 'CHANGES_REQUESTED').length;
    document.getElementById('prCount').textContent = `${allPRs.length} open · ${readyCount} ready`;
    if (!allPRs.length) { el.innerHTML = '<div class="empty">no open PRs</div>'; renderActivity(); return; }
    el.innerHTML = allPRs.map(pr => {
      const decision = pr.reviewDecision || '';
      const decBadge = decision ? `<span class="b ${decision.toLowerCase()}">${decision.replace('_',' ').toLowerCase()}</span>` : '';
      const ciBadge = `<span class="b ci-${pr.ci}">CI: ${pr.ci}</span>`;
      const draftBadge = pr.isDraft ? '<span class="b draft">draft</span>' : '';
      const mergeable = pr.mergeable === 'MERGEABLE';
      const mergeDisabled = !mergeable || pr.isDraft || decision === 'CHANGES_REQUESTED';
      const ready = mergeable && !pr.isDraft && pr.ci === 'pass' && decision !== 'CHANGES_REQUESTED';
      const reviewed = !!pr.reviewed_by_codex;
      const reviewUrl = pr.review_url || pr.url + '#issuecomment';
      const reviewBadge = reviewed
        ? `<a href="${escapeHtml(reviewUrl)}" target="_blank" class="b reviewed" title="an agent already posted a verdict on this PR — click to open">reviewed ✓</a>`
        : '';
      const reviewTitle = reviewed
          ? `Already reviewed — re-run only if the diff changed materially. Click "reviewed ✓" badge to read the verdict.`
          : `Run the selected agent interactively over the PR diff + issue body. It writes its verdict to a file; after the agent exits, the wrapper auto-posts the verdict to the PR and captures the comment URL.`;
      const metaBits = [];
      if (pr.author) metaBits.push(`by ${pr.author}`);
      if (pr.headRefName) metaBits.push(`branch ${pr.headRefName}`);
      if (pr.updatedAt) metaBits.push(`updated ${fmtAgo(pr.updatedAt)} ago`);
      const failing = (pr.failing_checks || []).length ? `failing: ${pr.failing_checks.join(', ')}` : '';
      const pending = (pr.pending_checks || []).length ? `pending: ${pr.pending_checks.join(', ')}` : '';
      const checks = failing || pending ? `<div class="checks">${escapeHtml(failing || pending)}</div>` : '';
      const fixTitle = pr.ci === 'fail'
        ? 'Run the selected agent against the failing checks and fix them in the branch'
        : 'Inspect the CI state and use the agent if the PR needs a repair';
      return `
        <div class="pr">
          <div class="ttl"><span class="num">#${pr.number}</span> <span class="title-text" title="${escapeHtml(pr.title + '\n' + (pr.summary || ''))}">${escapeHtml(pr.title)}</span> <a class="ext" href="${escapeHtml(pr.url)}" target="_blank" title="Open PR on GitHub">↗</a>${reviewBadge}</div>
          <div class="summary">${escapeHtml(pr.summary || 'no body yet')}</div>
          ${metaBits.length ? `<div class="meta">${escapeHtml(metaBits.join(' · '))}</div>` : ''}
          <div class="badges">${ready ? '<span class="b ready">ready</span>' : ''}${draftBadge}${decBadge}${ciBadge}</div>
          ${checks}
          <div class="row">
            <button class="review${reviewed ? ' done' : ''}" onclick="reviewPR(${pr.number})" title="${escapeHtml(reviewTitle)}">${reviewed ? '🔁 re-review' : '🔍 review'}</button>
            <button class="merge interactive" onclick="mergeInteractive(${pr.number})" title="Open an interactive agent session that merges PR #${pr.number} into main. If the squash-merge fails on conflicts, the agent rebases onto main, resolves conflicts (asking you if uncertain), pushes, and retries. Push notification fires when it needs you.">🟢 agent merge</button>
            <button class="fixci" onclick="fixCI(${pr.number})" title="${escapeHtml(fixTitle)}">${pr.ci === 'fail' ? '🩹 fix CI' : '🩹 inspect CI'}</button>
            <button class="merge" onclick="mergePR(${pr.number})" ${mergeDisabled ? 'disabled' : ''} title="${mergeDisabled ? 'PR is draft / not mergeable / changes requested' : 'gh pr merge --squash --delete-branch — no agent, just the gh call'}">✓ quick squash-merge</button>
            <button onclick="viewPRDiff(${pr.number})" title="Show the diff in the terminal pane">view diff</button>
          </div>
        </div>
      `;
    }).join('');
    renderActivity();
  } catch(e) { console.error(e); }
}

// Per-session PR metadata (set when the PTY is one of pr-review/merge-pr).
const sessionPRInfo = new Map();  // sid -> {pr, url, review_url_file, kind}

// Selected CLI agent (codex / claude / claude-minimax-free). Persists across reloads.
function currentAgent() {
  const el = document.getElementById('agentSelect');
  return (el && el.value) || localStorage.getItem('gitswarm.agent') || 'codex';
}
function agentLabel(id) {
  const el = document.getElementById('agentSelect');
  if (el) {
    const opt = el.querySelector(`option[value="${id}"]`);
    if (opt) return opt.textContent;
  }
  return id;
}

async function reviewPR(num) {
  requestNotifPermission();
  const ag = currentAgent();
  showToast(`preparing review for PR #${num} (${agentLabel(ag)})…`, '');
  try {
    const r = await fetch('/api/pty/new', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({kind:'pr-review', pr: num, agent: ag, rows: term.rows, cols: term.cols})
    });
    const data = await r.json();
    if (data.error) { showToast(`error: ${data.error}`, 'err'); return; }
    sessionPRInfo.set(data.sid, {pr: num, url: data.pr_url, review_url_file: data.review_url_file, kind: 'review', agent: data.agent || ag});
    showToast(`PR #${num} → ${agentLabel(data.agent || ag)} running. Verdict will auto-post on exit.`, 'ok');
    await listPtys();
    selectPty(data.sid, data.label || `review PR #${num}`);
  } catch(e) { showToast(`review failed: ${e}`, 'err'); }
}

async function mergeInteractive(num) {
  requestNotifPermission();
  const ag = currentAgent();
  if (!confirm(`Launch ${agentLabel(ag)} to merge PR #${num} into main? It will try gh pr merge first; on conflicts it rebases, asks you on non-mechanical conflicts, and retries.`)) return;
  showToast(`spawning ${agentLabel(ag)} merger for PR #${num}…`, '');
  try {
    const r = await fetch('/api/pty/new', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({kind:'merge-pr', pr: num, agent: ag, rows: term.rows, cols: term.cols})
    });
    const data = await r.json();
    if (data.error) { showToast(`error: ${data.error}`, 'err'); return; }
    sessionPRInfo.set(data.sid, {pr: num, url: data.pr_url, kind: 'merge', agent: data.agent || ag});
    showToast(`PR #${num} → ${agentLabel(data.agent || ag)} merger running. Notifications enabled for prompts.`, 'ok');
    await listPtys();
    selectPty(data.sid, data.label || `merge PR #${num}`);
  } catch(e) { showToast(`merge launch failed: ${e}`, 'err'); }
}

async function fixCI(num) {
  requestNotifPermission();
  const ag = currentAgent();
  showToast(`preparing CI fix for PR #${num} (${agentLabel(ag)})…`, '');
  try {
    const r = await fetch('/api/pty/new', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({kind:'ci-fix', pr: num, agent: ag, rows: term.rows, cols: term.cols})
    });
    const data = await r.json();
    if (data.error) { showToast(`error: ${data.error}`, 'err'); return; }
    sessionPRInfo.set(data.sid, {pr: num, url: data.pr_url, kind: 'fix-ci', agent: data.agent || ag});
    showToast(`PR #${num} → ${agentLabel(data.agent || ag)} CI fix running.`, 'ok');
    await listPtys();
    selectPty(data.sid, data.label || `fix CI PR #${num}`);
  } catch(e) { showToast(`CI fix launch failed: ${e}`, 'err'); }
}

async function mergePR(num) {
  if (!confirm(`Squash-merge PR #${num} into main and delete the branch? No agent — just gh pr merge. This is final.`)) return;
  showToast(`merging PR #${num}…`, '');
  try {
    const r = await fetch('/api/merge', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({pr: num, strategy: 'squash'})
    });
    const data = await r.json();
    if (data.error) { showToast(`merge error: ${data.error}`, 'err'); return; }
    showToast(`✓ merged #${num} (squash)`, 'ok');
    listPRs(); listIssues();
  } catch(e) { showToast(`merge failed: ${e}`, 'err'); }
}

// ---------- browser push notifications ----------
let _notifAsked = false;
function requestNotifPermission() {
  if (_notifAsked || !('Notification' in window)) return;
  _notifAsked = true;
  if (Notification.permission === 'default') {
    Notification.requestPermission().catch(()=>{});
  }
}
function fireNotif(title, body, onclick) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    const n = new Notification(title, {body, tag: title, renotify: false});
    if (onclick) n.onclick = () => { window.focus(); onclick(); n.close(); };
    setTimeout(() => n.close(), 12000);
  } catch(e) { console.warn('notif failed', e); }
}

// ---------- PR bar (clickable header above terminal) ----------
function renderPRBar(sid) {
  const bar = document.getElementById('pr-bar');
  const info = sessionPRInfo.get(sid);
  if (!info || !info.pr) { bar.className = ''; bar.innerHTML = ''; return; }
  const kindLabel = info.kind === 'review' ? 'reviewing'
    : (info.kind === 'merge' ? 'merging'
    : (info.kind === 'fix-ci' ? 'fixing CI' : 'working'));
  const prLink = info.url
    ? `<a href="${escapeHtml(info.url)}" target="_blank">PR #${info.pr} ↗</a>`
    : `PR #${info.pr}`;
  let verdictLink = '';
  if (info.review_url_file) {
    // Try to read the saved verdict URL — written only after codex exits + we posted.
    fetch('/api/file?name=' + encodeURIComponent('review-' + info.pr + '.url'))
      .then(r => r.ok ? r.text() : '')
      .then(txt => {
        const url = (txt || '').trim();
        if (url && /^https?:/.test(url)) {
          const verdictEl = document.getElementById('pr-bar-verdict');
          if (verdictEl) verdictEl.innerHTML = `<span class="sep">·</span><a class="verdict-link" href="${escapeHtml(url)}" target="_blank">verdict ↗</a>`;
        }
      }).catch(()=>{});
    verdictLink = `<span id="pr-bar-verdict"></span>`;
  }
  bar.className = 'show';
  const agentTag = info.agent ? agentLabel(info.agent) : 'agent';
  bar.innerHTML = `<b>${kindLabel}</b> ${prLink}<span class="sep">·</span>${agentTag}${verdictLink}`;
}

async function viewPRDiff(num) {
  // Spawn nothing — just write the diff to a state file and open it.
  showToast(`fetching diff for #${num}…`, '');
  try {
    const r = await fetch('/api/file?name=pr-' + num + '.diff');
    if (r.status === 404) {
      showToast(`no cached diff for #${num} — run review first`, 'err');
      return;
    }
    selectFile(`pr-${num}.diff`);
  } catch(e) { console.error(e); }
}

function escapeHtml(s) { return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function showToast(msg, kind) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = kind || '';
  t.style.display = 'block';
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => t.style.display = 'none', 5000);
}

async function launchIssue(num, mode) {
  showToast(`launching issue #${num} (${mode})…`, '');
  try {
    const r = await fetch('/api/launch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({issue: num, mode})
    });
    const data = await r.json();
    if (data.error) {
      showToast(`error: ${data.error}`, 'err');
      return;
    }
    showToast(`spawned on #${num} → ${data.implementer_log}`, 'ok');
    if (mode === 'watch') {
      // Wait briefly for the log file to appear, then auto-select it.
      setTimeout(() => selectFile(data.implementer_log), 1500);
    }
    listIssues();
    listFiles();
    listWorktrees();
  } catch(e) {
    showToast(`launch failed: ${e}`, 'err');
  }
}

function stopStreams() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  ptyStreamGen++;        // invalidate any in-flight pty long-poll loop
  if (ptyAbort) { try { ptyAbort.abort(); } catch(e){} ptyAbort = null; }
}

function selectFile(name) {
  stopStreams();
  view = {kind: 'file', name};
  cursor = 0;
  replayMode = false;
  inputHandler = null;        // read-only — drop keystrokes
  document.getElementById('title').textContent = '📄 ' + name;
  document.querySelectorAll('aside .file').forEach(el => el.classList.toggle('active', el.dataset.name === name));
  document.querySelectorAll('aside .pty').forEach(el => el.classList.remove('active'));
  document.getElementById('pr-bar').className = '';
  attachTerm();
  term.reset();
  pollOnce();
  pollTimer = setInterval(pollOnce, 800);
}

function selectPty(sid, label) {
  stopStreams();
  view = {kind: 'pty', sid, label};
  cursor = 0;
  replayMode = false;
  // PTY mode — keystrokes go to backend.
  inputHandler = (data) => {
    fetch('/api/pty/input', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({sid, data})}).catch(()=>{});
  };
  document.getElementById('title').textContent = '💻 ' + (label || sid);
  document.querySelectorAll('aside .file').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('aside .pty').forEach(el => el.classList.toggle('active', el.dataset.sid === sid));
  renderPRBar(sid);
  attachTerm();
  term.reset();
  // Defer the resize until after attach so xterm rows/cols are populated.
  setTimeout(sendResize, 50);
  streamPty();
}

async function streamPty() {
  const gen = ++ptyStreamGen;
  const sid = view.sid;
  // Long-poll loop, ~15s timeout per request server-side.
  while (gen === ptyStreamGen && view && view.kind === 'pty' && view.sid === sid) {
    try {
      ptyAbort = new AbortController();
      const r = await fetch('/api/pty/stream?sid=' + encodeURIComponent(sid) + '&offset=' + cursor + '&timeout=15',
                            {signal: ptyAbort.signal});
      if (!r.ok) {
        if (r.status === 404) { showToast('session ended', 'err'); return; }
        await new Promise(rs => setTimeout(rs, 1000));
        continue;
      }
      const reset = r.headers.get('X-Reset') === '1';
      const newOffset = parseInt(r.headers.get('X-Offset') || '0', 10);
      const alive = r.headers.get('X-Alive') === '1';
      const buf = await r.arrayBuffer();
      if (reset) {
        term.reset();
        term.write('\r\n[reconnect: dropped earlier output]\r\n');
      }
      if (buf.byteLength > 0) {
        // xterm.write accepts Uint8Array directly and decodes UTF-8, and
        // handles scroll behavior natively: stays pinned to the bottom when
        // the user is at the bottom, preserves position when they've scrolled
        // up. Don't call scrollToBottom() — that's what was overriding their
        // scroll. The "↓ bottom" button in the header is the manual catch-up.
        term.write(new Uint8Array(buf));
      }
      cursor = newOffset;
      if (!alive) {
        term.write('\r\n\x1b[33m[session ended]\x1b[0m\r\n');
        listPtys();
        return;
      }
    } catch(e) {
      if (e.name === 'AbortError') return;
      await new Promise(rs => setTimeout(rs, 800));
    }
  }
}

async function pollOnce() {
  if (!view || view.kind !== 'file' || replayMode) return;
  try {
    const r = await fetch('/api/file?name=' + encodeURIComponent(view.name) + '&offset=' + cursor);
    const text = await r.text();
    if (text.length > 0) {
      term.write(text);
      cursor += new TextEncoder().encode(text).length;
      // No forced scroll — xterm preserves the user's scroll position if they've scrolled up.
    }
  } catch(e) { console.error(e); }
}

async function replay() {
  if (!view || view.kind !== 'file') { showToast('replay only works for log files', 'err'); return; }
  if (pollTimer) clearInterval(pollTimer);
  replayMode = true;
  term.reset();
  cursor = 0;
  document.getElementById('replayBtn').classList.add('on');
  try {
    const r = await fetch('/api/file?name=' + encodeURIComponent(view.name));
    const text = await r.text();
    const chunkSize = 200;
    for (let i = 0; i < text.length; i += chunkSize) {
      term.write(text.slice(i, i + chunkSize));
      term.scrollToBottom();
      if (i % 4000 === 0) await new Promise(rs => setTimeout(rs, 8));
    }
    cursor = new TextEncoder().encode(text).length;
  } catch(e) { console.error(e); }
  document.getElementById('replayBtn').classList.remove('on');
  replayMode = false;
  if (follow) pollTimer = setInterval(pollOnce, 800);
}

// "follow" is now a one-shot jump-to-bottom. xterm auto-tails when the viewport
// is already at the bottom, and respects the user's position when they scroll
// up, so we just need a way to "snap back" when they want to catch up.
document.getElementById('followBtn').onclick = () => { if (termAttached) term.scrollToBottom(); };
document.getElementById('replayBtn').onclick = replay;
document.getElementById('clearBtn').onclick = () => { if (termAttached) { term.reset(); cursor = view && view.kind === 'pty' ? cursor : 0; } };
document.getElementById('killBtn').onclick = async () => {
  if (!view || view.kind !== 'pty') { showToast('not a pty session', 'err'); return; }
  if (!confirm('Close this terminal session? Any running command will be killed.')) return;
  await fetch('/api/pty/close', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sid: view.sid})});
  listPtys();
};

// Filter chip handlers
document.getElementById('filters').addEventListener('click', e => {
  if (e.target.tagName !== 'BUTTON') return;
  issueFilter = e.target.dataset.f;
  document.querySelectorAll('#filters button').forEach(b => b.classList.toggle('on', b.dataset.f === issueFilter));
  renderIssues();
});

const _prevPtyAlive = new Map();  // sid -> bool, used to detect alive→dead transitions
async function listPtys() {
  try {
    const r = await fetch('/api/pty/list');
    const data = await r.json();
    const el = document.getElementById('ptys');
    const sessions = data.sessions || [];
    allPtys = sessions;
    // Detect alive→dead transitions and fire notifications, then refresh PRs
    // so the reviewed badge appears if the session just posted a verdict.
    let didTransition = false;
    let idleCount = 0;
    const now = Date.now();
    for (const s of sessions) {
      const prev = _prevPtyAlive.get(s.sid);
      if (prev === true && !s.alive) {
        didTransition = true;
        const info = sessionPRInfo.get(s.sid);
        const title = info && info.pr
          ? `codex ${info.kind} finished · PR #${info.pr}`
          : `codex session finished`;
        const body = s.label || s.sid;
        fireNotif(title, body, () => selectPty(s.sid, s.label));
      }
      _prevPtyAlive.set(s.sid, s.alive);

      const state = idleState.get(s.sid) || {lastOutput: 0, notified: false};
      if (state.lastOutput !== s.last_output) {
        state.lastOutput = s.last_output;
        state.notified = false;
      }
      if (s.alive && s.last_output && (now - s.last_output * 1000) > 30000) {
        idleCount++;
        if (!state.notified) {
          const info = sessionPRInfo.get(s.sid) || {};
          const title = info.pr
            ? `codex ${info.kind || 'session'} needs you · PR #${info.pr}`
            : `codex session needs you`;
          fireNotif(title, s.label || s.sid, () => selectPty(s.sid, s.label));
          state.notified = true;
        }
      }
      idleState.set(s.sid, state);
    }
    if (didTransition) { listPRs(); listIssues(); }
    document.getElementById('needsCount').textContent = `${idleCount} idle`;
    if (!sessions.length) {
      document.getElementById('needsCount').textContent = '0 idle';
      renderNeedsMe();
      renderActivity();
      el.innerHTML = '<div class="empty">no terminals · click + new shell</div>';
      return;
    }
    el.innerHTML = sessions.map(s => {
      const cwd = s.cwd.replace(/^.*?\.agent-worktrees\//, '.agent-worktrees/').replace(/^.*?\/__REPO_NAME__\/(?:\.claude\/worktrees\/[^/]+\/)?/, '');
      const label = s.label || s.sid;
      const dot = s.alive ? '<span style="color:#3fb950;">●</span>' : '<span style="color:#6e7681;">○</span>';
      const cls = (view && view.kind === 'pty' && view.sid === s.sid) ? 'pty active' : 'pty';
      // No inline onclick — handled by event delegation. data-* attrs are
      // HTML-escaped, so labels containing quotes / unicode no longer break
      // the attribute parsing (the previous bug: JSON.stringify(label) injected
      // raw " into a double-quoted attr, closing it early).
      const tip = s.alive
        ? `Attach the terminal pane to this live session. PID running in ${cwd}.`
        : `Session ended. Click to view its scrollback (no new input possible).`;
      return `<div class="${cls}" data-sid="${escapeHtml(s.sid)}" data-label="${escapeHtml(label)}" title="${escapeHtml(tip)}">${dot} ${escapeHtml(label)}<div class="meta">${escapeHtml(cwd)}</div></div>`;
    }).join('');
    renderNeedsMe();
    renderActivity();
  } catch(e) { console.error(e); }
}

function renderNeedsMe() {
  const el = document.getElementById('needsme');
  const sessions = allPtys.filter(s => s.alive && s.last_output && (Date.now() - s.last_output * 1000) > 30000);
  if (!sessions.length) {
    el.innerHTML = '<div class="empty">nothing waiting right now</div>';
    return;
  }
  el.innerHTML = sessions.map(s => {
    const info = sessionPRInfo.get(s.sid) || {};
    const label = s.label || s.sid;
    const kind = info.kind || 'session';
    const meta = [];
    if (info.pr) meta.push(`PR #${info.pr}`);
    if (info.issue) meta.push(`issue #${info.issue}`);
    if (s.cwd) meta.push(s.cwd.replace(/^.*?\/__REPO_NAME__\//, ''));
    return `<div class="session">
      <div class="title"><span class="name">${escapeHtml(label)}</span><span class="idle">${escapeHtml(fmtIdle(s.last_output * 1000))}</span></div>
      <div class="status">${escapeHtml(kind)}</div>
      ${meta.length ? `<div class="meta-line">${escapeHtml(meta.join(' · '))}</div>` : ''}
      <button data-sid="${escapeHtml(s.sid)}" data-label="${escapeHtml(label)}" onclick="selectPty(this.dataset.sid, this.dataset.label)">focus</button>
    </div>`;
  }).join('');
}

function renderActivity() {
  const items = [];
  for (const it of allIssues) {
    const ts = it.updatedAt ? new Date(it.updatedAt).getTime() : 0;
    if (!ts) continue;
    items.push({
      ts,
      kind: 'issue',
      title: `#${it.number} ${it.title}`,
      detail: it.summary || '',
      href: it.url,
    });
  }
  for (const pr of allPRs) {
    const ts = pr.updatedAt ? new Date(pr.updatedAt).getTime() : 0;
    if (!ts) continue;
    items.push({
      ts,
      kind: 'pr',
      title: `PR #${pr.number} ${pr.title}`,
      detail: pr.summary || '',
      href: pr.url,
    });
  }
  for (const s of allPtys) {
    const ts = (s.last_output || s.started || 0) * 1000;
    if (!ts) continue;
    items.push({
      ts,
      kind: 'pty',
      title: s.label || s.sid,
      detail: s.cwd.replace(/^.*?\/__REPO_NAME__\//, ''),
      sid: s.sid,
      label: s.label || s.sid,
    });
  }
  items.sort((a, b) => b.ts - a.ts);
  const top = items.slice(0, 8);
  document.getElementById('activityCount').textContent = `${top.length} recent`;
  const el = document.getElementById('activity');
  if (!top.length) { el.innerHTML = '<div class="empty">nothing recent yet</div>'; return; }
  el.innerHTML = top.map(item => {
    const kind = item.kind === 'issue' ? 'issue' : item.kind === 'pr' ? 'pr' : 'pty';
    const link = item.kind === 'pty'
      ? `<button data-sid="${escapeHtml(item.sid)}" data-label="${escapeHtml(item.label)}" onclick="selectPty(this.dataset.sid, this.dataset.label)">focus</button>`
      : `<button data-href="${escapeHtml(item.href)}" onclick="window.open(this.dataset.href, '_blank')">open</button>`;
    return `<div class="activity-item">
      <div class="head"><span class="title">${escapeHtml(item.title)}</span><span class="kind">${kind} · ${escapeHtml(fmtAgo(item.ts))} ago</span></div>
      <div class="meta-line">${escapeHtml(item.detail || '')}</div>
      ${link}
    </div>`;
  }).join('');
}

// Event delegation for PTY rows — survives re-renders by listPtys().
document.getElementById('ptys').addEventListener('click', (e) => {
  const row = e.target.closest('.pty');
  if (!row) return;
  selectPty(row.dataset.sid, row.dataset.label);
});

async function newShell(cwd, label) {
  showToast('spawning shell…', '');
  try {
    const r = await fetch('/api/pty/new', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({kind:'shell', cwd, rows: term.rows, cols: term.cols})});
    const data = await r.json();
    if (data.error) { showToast('error: ' + data.error, 'err'); return; }
    showToast('shell open ✓', 'ok');
    await listPtys();
    selectPty(data.sid, data.label || label);
  } catch(e) { showToast('shell failed: ' + e, 'err'); }
}

async function openWorktreeShell(wtName) {
  // Server resolves this relative path against REPO_ROOT.
  await newShell('.agent-worktrees/' + wtName, 'shell · ' + wtName);
}

async function newAgentShell(cwd) {
  const ag = currentAgent();
  showToast(`spawning ${agentLabel(ag)}…`, '');
  try {
    const r = await fetch('/api/pty/new', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({kind:'agent-shell', agent: ag, cwd, rows: term.rows, cols: term.cols})});
    const data = await r.json();
    if (data.error) { showToast('error: ' + data.error, 'err'); return; }
    showToast(`${agentLabel(data.agent || ag)} open ✓`, 'ok');
    await listPtys();
    selectPty(data.sid, data.label || `${ag} · repo root`);
  } catch(e) { showToast('agent launch failed: ' + e, 'err'); }
}

async function launchIssueShell(num) {
  const ag = currentAgent();
  showToast(`preparing worktree for #${num} + launching ${agentLabel(ag)}…`, '');
  try {
    const r = await fetch('/api/pty/new', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({kind:'issue-shell', issue: num, agent: ag, rows: term.rows, cols: term.cols})});
    const data = await r.json();
    if (data.error) { showToast('error: ' + data.error, 'err'); return; }
    showToast(`#${num} → ${agentLabel(data.agent || ag)} running interactively`, 'ok');
    sessionPRInfo.set(data.sid, {issue: num, branch: data.branch, kind: 'issue', url: data.issue_url || '', agent: data.agent || ag});
    await listPtys();
    selectPty(data.sid, data.label || `#${num}`);
    listIssues(); listWorktrees();
  } catch(e) { showToast('launch failed: ' + e, 'err'); }
}

async function proposeIssue() {
  const hint = (prompt('rough slug for the new issue (lowercase, dashes — the agent will write the real title). Leave blank for a timestamped draft.', '') || '').trim();
  if (hint === null) return;
  const ag = currentAgent();
  showToast(`spawning ${agentLabel(ag)} to draft a new issue…`, '');
  try {
    const r = await fetch('/api/pty/new', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({kind:'propose-issue', slug: hint, agent: ag, rows: term.rows, cols: term.cols})});
    const data = await r.json();
    if (data.error) { showToast('error: ' + data.error, 'err'); return; }
    showToast(`propose · ${data.slug} → ${agentLabel(data.agent || ag)} running. Draft: ${data.draft_file}`, 'ok');
    sessionPRInfo.set(data.sid, {kind: 'propose', slug: data.slug, agent: data.agent || ag});
    await listPtys();
    selectPty(data.sid, data.label || `propose · ${data.slug}`);
    listFiles();
  } catch(e) { showToast('propose failed: ' + e, 'err'); }
}

async function batchClaimNext() {
  const count = parseInt(prompt('Launch how many claim-next issues?', '3'), 10);
  if (!Number.isFinite(count) || count <= 0) return;
  const issues = allIssues.filter(it => it.claim_next && !it.in_progress).slice(0, count);
  if (!issues.length) { showToast('no claim-next issues available', 'err'); return; }
  if (!confirm(`Launch ${issues.length} issue shell${issues.length === 1 ? '' : 's'}?`)) return;
  for (let i = 0; i < issues.length; i++) {
    await launchIssueShell(issues[i].number);
    if (i < issues.length - 1) await new Promise(rs => setTimeout(rs, 800));
  }
}

async function removeWorktree(name, quiet) {
  if (!quiet && !confirm(`Remove worktree ${name}? The branch stays around so it can be recreated later.`)) return;
  try {
    const r = await fetch('/api/worktree/remove', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name})
    });
    const d = await r.json();
    if (d.error) { showToast('error: ' + d.error, 'err'); return; }
    showToast(`removed worktree ${name}`, 'ok');
    listWorktrees();
  } catch(e) { showToast('remove failed: ' + e, 'err'); }
}

async function cleanupState(dryRun) {
  const days = parseInt(prompt(dryRun ? 'audit state files older than how many days?' : 'PRUNE state files older than how many days? (deletes implementer/orchestrator logs, prompts, diffs, drafts)', '7'), 10);
  if (!Number.isFinite(days) || days < 0) return;
  if (!dryRun && !confirm(`Delete state files older than ${days} day(s)? Worktrees and .gitignore are untouched.`)) return;
  try {
    const r = await fetch('/api/state/cleanup', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({stale_days: days, dry_run: !!dryRun})});
    const d = await r.json();
    if (d.error) { showToast('error: ' + d.error, 'err'); return; }
    const mb = (d.freed_bytes / 1048576).toFixed(2);
    const verb = d.dry_run ? 'would free' : 'freed';
    showToast(`${verb} ${mb} MB · ${d.removed.length} file(s) ${d.dry_run ? 'flagged' : 'removed'} · ${d.kept_count} kept`, 'ok');
    if (d.removed.length) console.table(d.removed);
    listFiles();
  } catch(e) { showToast('cleanup failed: ' + e, 'err'); }
}

document.getElementById('newShellBtn').onclick = () => newShell(null, 'shell · repo root');
document.getElementById('newAgentBtn').onclick = () => newAgentShell(null);

// ---------- styled tooltip controller ----------
// One floating element, repositioned on hover. Reads from `title` (so every
// existing button/row gets a tooltip for free) and stashes the original onto
// `data-tip` to suppress the slow ugly native tooltip while keeping the value
// re-attachable on mouseleave (so screen readers + DevTools still see it).
const tipEl = document.getElementById('tip');
let tipTarget = null;

function showTip(target, text) {
  if (!text) { hideTip(); return; }
  tipTarget = target;
  tipEl.textContent = text;
  tipEl.style.display = 'block';
  // Force layout then position; default above the element, shifted left if it'd clip.
  const rect = target.getBoundingClientRect();
  const tipRect = tipEl.getBoundingClientRect();
  let left = rect.left + rect.width / 2 - tipRect.width / 2;
  let top  = rect.top - tipRect.height - 8;
  // Flip below if it'd go above the viewport.
  if (top < 4) top = rect.bottom + 8;
  // Clamp horizontally.
  left = Math.max(6, Math.min(left, window.innerWidth - tipRect.width - 6));
  tipEl.style.left = left + 'px';
  tipEl.style.top  = top  + 'px';
  requestAnimationFrame(() => tipEl.classList.add('show'));
}
function hideTip() {
  tipEl.classList.remove('show');
  tipEl.style.display = 'none';
  if (tipTarget && tipTarget.dataset.tip != null) {
    tipTarget.setAttribute('title', tipTarget.dataset.tip);
    delete tipTarget.dataset.tip;
  }
  tipTarget = null;
}
document.addEventListener('mouseover', (e) => {
  const t = e.target.closest('[title], [data-tip]');
  if (!t || t === tipTarget) return;
  // Pull title once and stash it so the native tooltip doesn't appear after a delay.
  let text = t.getAttribute('title');
  if (text) {
    t.dataset.tip = text;
    t.removeAttribute('title');
  } else {
    text = t.dataset.tip;
  }
  if (text) showTip(t, text);
});
document.addEventListener('mouseout', (e) => {
  if (!tipTarget) return;
  // Only hide when leaving the tipTarget entirely (not on transit between its children).
  if (!tipTarget.contains(e.relatedTarget)) hideTip();
});
window.addEventListener('scroll', hideTip, true);
window.addEventListener('blur', hideTip);

// Browsers gate Notifications behind a user gesture — ask on the first click.
window.addEventListener('click', () => requestNotifPermission(), {once: true, capture: true});

// Populate the agent dropdown from /api/agents. Disabled options for agents
// whose binary isn't on $PATH (still picks them up if the user adds them later).
async function loadAgents() {
  try {
    const r = await fetch('/api/agents');
    const d = await r.json();
    const sel = document.getElementById('agentSelect');
    if (!sel || !d.agents) return d;
    const saved = localStorage.getItem('gitswarm.agent');
    sel.innerHTML = d.agents.map(a => {
      const sfx = a.available ? '' : ` — not installed (${a.bin})`;
      return `<option value="${escapeHtml(a.id)}" ${a.available ? '' : 'disabled'}>${escapeHtml(a.label)}${escapeHtml(sfx)}</option>`;
    }).join('');
    // Choose: saved → first available → default
    const ids = d.agents.map(a => a.id);
    let pick = saved && ids.includes(saved) && d.agents.find(a => a.id === saved && a.available) ? saved : null;
    if (!pick) pick = (d.agents.find(a => a.available) || {}).id || d.default;
    sel.value = pick;
    sel.onchange = () => localStorage.setItem('gitswarm.agent', sel.value);
    return d;
  } catch(e) { console.warn('loadAgents failed', e); }
}

// Dev-reload: poll /api/agents for the gitswarm code mtime. If it changes
// (the user or an AI edited ui.py / server.py / github.py and restarted the
// server), reload the page so the new UI is picked up without manual refresh.
let _codeMtime = 0;
async function checkCodeMtime() {
  try {
    const r = await fetch('/api/agents');
    const d = await r.json();
    if (!d || !d.code_mtime) return;
    if (_codeMtime && d.code_mtime > _codeMtime + 0.5) {
      console.log('gitswarm code changed — reloading');
      location.reload();
      return;
    }
    _codeMtime = d.code_mtime;
  } catch(e) {}
}

loadAgents().then(d => { if (d && d.code_mtime) _codeMtime = d.code_mtime; });
listFiles(); listWorktrees(); listIssues(); listPRs(); listPtys();
setInterval(listFiles, 5000);
setInterval(listWorktrees, 4000);
setInterval(listIssues, 8000);
setInterval(listPRs, 10000);
setInterval(listPtys, 3000);
setInterval(checkCodeMtime, 4000);
</script>
</body></html>"""
