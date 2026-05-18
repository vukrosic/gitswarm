# React + TypeScript UI Refactor Plan

## Why this refactor exists

`gitswarm` is becoming an agent operating dashboard, not a small static page.
The current dashboard works, but most of the UI lives inside one large
`INDEX_HTML` string in `ui.py`. That made the first version fast to build, but
it makes future feature growth expensive:

- every feature touches the same file;
- agents conflict with each other when they all edit `ui.py`;
- API shapes are implicit in JavaScript code instead of shared contracts;
- UI state, rendering, and network calls are intertwined;
- testing individual panes is hard.

The target is a React + TypeScript frontend under `web/`, backed by the
existing Python server and GitHub helpers. The current `web/src` directory
shape is not binding. It can be replaced if a different structure makes the
React app easier to scale and easier for agents to work on in parallel.

The Python package should stay lean. Do not turn `gitswarm` into a heavy web
app stack. The refactor should preserve the smallest useful workflow while
making the codebase ready for many more dashboard features and many parallel
AI-agent contributors.

## Core direction

Build a real frontend application in a structure like this:

```text
web/
  package.json
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api/
    components/
    hooks/
    panes/
    state/
    styles/
    types/
```

This is a recommended shape, not a sacred one. If the first React branch has
empty folders, partial scaffolding, or awkward boundaries, replace them. The
constraint is the desired architecture and workflow, not the current placeholder
tree.

Keep the backend in:

```text
server.py
github.py
dashboard.py
bin/gitswarm.js
```

Use `shared/api-contract.md` as the human-readable source of truth for the
HTTP API. Add generated or hand-written TypeScript API types under
`web/src/types/` and keep them aligned with `shared/api-contract.md`.

The final dashboard should still be launched by:

```bash
npx gitswarm
gitswarm --repo /path/to/repo
./scripts/dev.sh 7777
```

## Non-negotiables

- Use React and TypeScript for the new dashboard.
- Keep the published npm package lean.
- Avoid adding runtime dependencies to the Python/backend package.
- Frontend build dependencies are allowed only under `web/`.
- Keep `state/`, `.gitswarm/`, and `.agent-worktrees/` local-only.
- Do not hardcode the source repo name; the dashboard must run against the
  current git checkout.
- Preserve current API behavior while moving the UI.
- Keep the existing Python dashboard usable until the React UI reaches parity.
- Restart the dashboard after edits to `ui.py`, `server.py`, or `github.py`.

## Migration strategy

Do this as a strangler migration. React should grow beside the current
`ui.py` dashboard until it can replace it.

1. Create or replace the React + TypeScript app skeleton under `web/`.
2. Add a backend route or dev proxy that can serve the React app without
   breaking the current dashboard.
3. Extract API clients and types first.
4. Port one pane at a time.
5. Keep old `ui.py` behavior as the oracle while React catches up.
6. Once React has feature parity, reduce `ui.py` to a minimal HTML shell or
   remove the embedded dashboard.

## Target architecture

```text
Python backend
  server.py
    owns HTTP routes, PTY sessions, static file serving
  github.py
    owns GitHub, git, worktree, issue, PR, and prompt preparation

Shared contract
  shared/api-contract.md
    documents every /api endpoint and response shape

React frontend
  web/src/api/
    typed fetch wrappers for /api/*
  web/src/types/
    Issue, PullRequest, Worktree, PtySession, Agent, FileEntry
  web/src/hooks/
    polling, PTY streaming, persisted preferences
  web/src/panes/
    IssuesPane, PullRequestsPane, WorktreesPane, TerminalPane, FilesPane
  web/src/components/
    small reusable controls and rows
  web/src/state/
    thin local state helpers for selection, filters, session metadata
  web/src/styles/
    dashboard CSS split by surface or token file
```

Keep state boring. Prefer React state plus small custom hooks before adding a
global state library. Add a state library only if the app clearly outgrows
simple hooks.

## Parallel agent workstreams

These lanes are designed so multiple agents can work at the same time with low
conflict risk. Each lane should become one GitHub issue or one agent branch.

Use the lane code in every issue title:

```text
[react-ui][A] Frontend scaffold and folder reset
[react-ui][B] API types and client
[react-ui][F] Terminal and PTY streaming
```

Use labels to make the dashboard filterable:

- `react-ui`
- `agent-friendly`
- `claim-next`
- `lane:A`, `lane:B`, `lane:C`, and so on
- `parallel:foundation`, `parallel:panes`, `parallel:cutover-risk`, or
  `parallel:cutover`
- `blocked` only when the issue cannot start yet

Each lane issue should say whether it is `independent`, `starts-after`, or
`blocks` another lane. This matters more than the milestone because agents need
to know what can run right now.

## Lane index

| Lane | Issue title suffix | Parallel group | Can start when | Primary ownership |
| --- | --- | --- | --- | --- |
| A | Frontend scaffold and folder reset | foundation | now | `web/package.json`, `web/src/App.tsx`, app shell |
| B | API types and client | foundation | now | `shared/api-contract.md`, `web/src/types/`, `web/src/api/` |
| C | Server static build integration | foundation | after A has a build shape | `server.py`, `dashboard.py`, `bin/gitswarm.js`, `scripts/dev.sh` |
| D | Issues pane | panes | after A and B | issue components, issue hooks |
| E | Pull request pane | panes | after A and B | PR components, PR hooks |
| F | Terminal and PTY streaming | cutover-risk | after A, can begin before D/E finish | terminal pane, PTY hooks |
| G | Worktrees and files panes | panes | after A and B | worktree/file panes and hooks |
| H | Agent launch flows | cutover-risk | after A, B, and enough terminal shell exists | agent selector, launch helpers |
| I | Styling and design system | foundation/panes | after A, then continues alongside panes | CSS variables, primitives |
| J | Verification and parity harness | cutover | after A, expands as panes land | tests, smoke scripts, parity checklist |

### Lane A: Frontend scaffold and folder reset

Ownership:

- `web/package.json`
- `web/tsconfig.json`
- `web/vite.config.ts`
- `web/index.html`
- `web/src/main.tsx`
- `web/src/App.tsx`
- `web/src/styles/`

Tasks:

- create a Vite React + TypeScript app;
- remove or replace any existing empty/incorrect frontend scaffolding;
- add build and dev scripts;
- add a minimal dashboard shell with the existing three-column layout;
- keep styling local to `web/`;
- add a `web` build output that Python can serve later.

Acceptance:

- `cd web && npm install && npm run build` succeeds;
- the app renders a static shell without API data;
- no backend behavior changes.

### Lane B: API types and client

Ownership:

- `shared/api-contract.md`
- `web/src/types/`
- `web/src/api/`

Tasks:

- define TypeScript interfaces for every documented `/api/*` shape;
- add typed `fetchJson`, `postJson`, and text/binary helpers;
- keep endpoint names centralized;
- add lightweight runtime error handling for API failures.

Acceptance:

- TypeScript catches wrong response fields in UI code;
- all current documented endpoints have client functions;
- contract changes are reflected in both `shared/api-contract.md` and TS types.

### Lane C: Server static build integration

Ownership:

- `server.py`
- `dashboard.py`
- `bin/gitswarm.js`
- `scripts/dev.sh`
- package publish config if needed

Tasks:

- serve the React build in production mode;
- preserve the current dashboard route while migration is incomplete;
- add a dev mode that proxies or serves Vite cleanly;
- ensure `gitswarm --repo /path/to/repo` still works.

Acceptance:

- existing Python dashboard still runs;
- React dashboard can be opened from the same backend;
- `npm test` still passes;
- published package includes only needed runtime files.

### Lane D: Issues pane

Ownership:

- `web/src/panes/IssuesPane.tsx`
- `web/src/components/IssueRow.tsx`
- `web/src/components/IssueReadModal.tsx`
- issue-related hooks under `web/src/hooks/`

Tasks:

- port issue list rendering;
- support filters such as `claim-next`, `in-progress`, and parked states;
- port claim, review, watch, background, read modal, and GitHub link actions;
- keep all issue actions wired through typed API clients.

Acceptance:

- issue list reaches current UI parity;
- actions call the same backend routes as `ui.py`;
- visual claimed/in-progress states remain obvious.

### Lane E: Pull request pane

Ownership:

- `web/src/panes/PullRequestsPane.tsx`
- `web/src/components/PullRequestRow.tsx`
- PR-related hooks under `web/src/hooks/`

Tasks:

- port PR list rendering;
- support review, merge, fix CI, and diff view actions;
- show branch, author, labels, draft/mergeability/check status where available;
- keep conservative disabling rules for risky actions.

Acceptance:

- PR workflow reaches current UI parity;
- quick merge and agent merge flows remain distinct;
- diff viewing works without a new dependency.

### Lane F: Terminal and PTY streaming

Ownership:

- `web/src/panes/TerminalPane.tsx`
- `web/src/hooks/usePtyStream.ts`
- `web/src/hooks/usePtySessions.ts`
- terminal-specific components

Tasks:

- port xterm setup and teardown;
- implement streaming with offsets, reset handling, dropped byte handling, and
  alive/dead session state;
- support session selection, closing, and reconnecting;
- preserve current middle-pane versus dock behavior if still needed.

Acceptance:

- live output streams correctly;
- typing into a live PTY works;
- reload/reconnect behavior is at least as good as current `ui.py`;
- no duplicated output after polling resets.

### Lane G: Worktrees and files panes

Ownership:

- `web/src/panes/WorktreesPane.tsx`
- `web/src/panes/FilesPane.tsx`
- worktree/file components and hooks

Tasks:

- port worktree list, status display, prune actions, and running markers;
- port state file list and tailing behavior;
- keep file viewing safe and path-limited through backend APIs.

Acceptance:

- worktrees match the current backend response;
- state files can be opened and tailed;
- prune actions preserve current confirmations and safety rules.

### Lane H: Agent launch flows

Ownership:

- `web/src/components/AgentSelector.tsx`
- `web/src/hooks/useAgents.ts`
- launch/review/merge/propose/fix-CI action helpers

Tasks:

- port agent selector and saved preference;
- port claim, batch claim, propose, review, merge, fix CI, and new shell launch
  flows;
- keep session metadata so launched sessions open in the correct pane.

Acceptance:

- every launch button creates the same kind of session as today;
- localStorage preference behavior is preserved;
- failures show actionable UI feedback.

### Lane I: Styling and design system

Ownership:

- `web/src/styles/`
- reusable presentational components

Tasks:

- extract colors, spacing, borders, and text sizes into CSS variables;
- define consistent button, badge, row, panel, modal, and tab styles;
- preserve the operational dashboard feel: dense, scannable, and calm;
- avoid marketing-page layout or oversized decorative UI.

Acceptance:

- all panes use shared visual primitives;
- no repeated one-off button or badge styling across panes;
- text fits in dense rows on desktop and reasonable narrow widths.

### Lane J: Verification and parity harness

Ownership:

- `scripts/`
- test config under `web/`
- optional smoke docs under `docs/`

Tasks:

- add frontend typecheck/build checks;
- add smoke checks for Python API plus React build;
- create a manual parity checklist against the old dashboard;
- optionally add browser smoke tests once the app has enough UI.

Acceptance:

- root `npm test` includes React build/typecheck when `web/` is present;
- smoke checks are reproducible from a clean checkout;
- parity checklist covers issues, PRs, PTYs, files, worktrees, and launches.

## GitHub milestones

Use multiple milestones, but keep them phase-based rather than lane-based.
Milestones should answer "what release checkpoint is this for?" Labels and lane
codes should answer "which agent can work on this independently?"

Recommended milestones:

- `React UI 1 - Foundation`: lanes A, B, C, and the first pass of I.
- `React UI 2 - Pane parity`: lanes D, E, G, and continued I.
- `React UI 3 - Terminal, launch, cutover`: lanes F, H, J, final parity, and
  the switch from `ui.py` to React.

Do not create one milestone per lane. That makes GitHub look organized, but it
does not express dependencies well and it fragments the migration. Lanes should
be labels and issue-title codes; milestones should be checkpoints.

If the repo needs a simpler view, use one milestone named `React UI Migration`
and rely entirely on lane labels. For this project, three milestones are better:
they let agents run in parallel while still giving you a visible path from
foundation to cutover.

## Execution order

Start together:

- Lane A: Frontend scaffold and folder reset
- Lane B: API types and client
- Lane I: Styling primitives, first pass only

Start after Lane A has a build shape:

- Lane C: Server static build integration
- Lane F: Terminal and PTY streaming investigation

Start after Lane A and Lane B land:

- Lane D: Issues pane
- Lane E: Pull request pane
- Lane G: Worktrees and files panes

Start after the app shell, API client, and terminal basics exist:

- Lane H: Agent launch flows
- Lane J: Verification and parity harness

Lane F should not wait until the end. PTY streaming is the riskiest part of the
UI, and it should shape the app shell and state model before the migration
hardens.

## Issue body template

Use this shape when creating the GitHub issues:

````markdown
# [react-ui][LANE] Short task title

### Goal
One sentence describing the user-visible or architecture-visible outcome.

### Parallelization
- Lane: A/B/C/etc.
- Parallel group: foundation/panes/cutover-risk/cutover
- Status: independent | starts-after Lane X | blocks Lane Y
- Safe to run with: Lane X, Lane Y
- Do not edit: files owned by other active lanes

### Owned files
- `path/to/file`

### Endpoints used
- `GET /api/issues`
- `POST /api/launch`

### Current behavior to match
Short note pointing to the current `ui.py` behavior or backend route.

### Acceptance criteria
- Verifiable outcome 1.
- Verifiable outcome 2.

### Anti-features
- Boundary 1.
- Boundary 2.

### Verification
```bash
npm test
cd web && npm run build
```
````

## Agent coordination rules

Each agent issue should include:

- exact owned files;
- endpoints used;
- acceptance criteria;
- anti-features;
- verification command;
- current `ui.py` behavior to match.

Agents should avoid editing shared files unless their lane owns them. The
current `web/src` folders may be deleted, renamed, or rebuilt by Lane A before
other frontend lanes begin. After Lane A lands, later agents should respect the
new frontend boundaries.

Shared files that need extra care:

- `server.py`
- `github.py`
- `ui.py`
- `web/src/App.tsx`
- `web/src/styles/*`
- `shared/api-contract.md`

When a lane needs a shared file change, the issue should say so explicitly.
Otherwise agents should add new files under their lane and wire them through
the smallest shared integration point.

## What should not happen

- Do not rewrite the Python backend just because the frontend is changing.
- Do not introduce a database for dashboard state.
- Do not move `.gitswarm/state/` into the package.
- Do not add a full design system package.
- Do not add a router until there are real pages.
- Do not add a global state library before hooks become painful.
- Do not break the current dashboard before the React dashboard is usable.

## Definition of done

The refactor is complete when:

- the default dashboard is React + TypeScript;
- `ui.py` no longer contains the main application logic;
- the Python backend remains the single local orchestrator;
- all documented `/api/*` endpoints have typed frontend callers;
- root verification covers Python syntax, shell scripts, Node entrypoint, and
  React build/typecheck;
- agents can add new dashboard features by owning one pane or API slice instead
  of editing one giant HTML string.
