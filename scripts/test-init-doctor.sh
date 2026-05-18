#!/usr/bin/env bash
set -euo pipefail

root="/Users/vukrosic/my-life/gitswarm"
tmprepo="$(mktemp -d)"
tmpbin="$(mktemp -d)"
trap 'rm -rf "$tmprepo" "$tmpbin"' EXIT

git init -q "$tmprepo"
repo_real="$(python3 - "$tmprepo" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
)"

cat > "$tmpbin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "$1 $2" in
  "auth status")
    exit 0
    ;;
  "repo view")
    cat <<'JSON'
{"nameWithOwner":"vukrosic/gitswarm","url":"https://github.com/vukrosic/gitswarm","defaultBranchRef":{"name":"main"}}
JSON
    ;;
  "issue list")
    cat <<'JSON'
[{"number":1}]
JSON
    ;;
  "pr list")
    cat <<'JSON'
[{"number":2}]
JSON
    ;;
  *)
    echo "unexpected gh call: $*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$tmpbin/gh"

GITSWARM_GH_BIN="$tmpbin/gh" node "$root/bin/gitswarm.js" init --repo "$tmprepo" >"$tmprepo/init.out"
test -f "$tmprepo/.gitswarm/config.json"
test -d "$tmprepo/.gitswarm/state"
test -d "$tmprepo/.agent-worktrees"

python3 - "$tmprepo/.gitswarm/config.json" "$repo_real" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
assert data["repo_root"] == sys.argv[2]
assert data["dashboard_port"] == 7777
assert data["state_dir"] == ".gitswarm/state"
assert data["worktree_dir"] == ".agent-worktrees"
PY

GITSWARM_GH_BIN="$tmpbin/gh" node "$root/bin/gitswarm.js" doctor --repo "$tmprepo" >"$tmprepo/doctor.out"
grep -F "config: present" "$tmprepo/doctor.out"
grep -F "gh auth: ok" "$tmprepo/doctor.out"
grep -F "gh repo: vukrosic/gitswarm" "$tmprepo/doctor.out"
grep -F "gh issues: ok" "$tmprepo/doctor.out"
grep -F "gh prs: ok" "$tmprepo/doctor.out"
grep -F "local dirs: ok" "$tmprepo/doctor.out"
