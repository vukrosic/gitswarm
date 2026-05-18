#!/usr/bin/env bash
set -euo pipefail

tmpdir="$(mktemp -d)"
out="$tmpdir/out.txt"
cleanup() {
  rm -rf "$tmpdir"
}
trap cleanup EXIT

git init -q "$tmpdir"

python3 - "$tmpdir" "$out" <<'PY'
import subprocess
import sys
import time
from pathlib import Path

repo = sys.argv[1]
out = Path(sys.argv[2])
root = Path('/Users/vukrosic/my-life/gitswarm')

with out.open('w') as fh:
    proc = subprocess.Popen(
        ['node', './bin/gitswarm.js', '--repo', repo, '0'],
        cwd=root,
        stdout=fh,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1.2)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
PY

grep -F "$tmpdir/.gitswarm/state" "$out"
grep -F "$tmpdir/.agent-worktrees" "$out"
