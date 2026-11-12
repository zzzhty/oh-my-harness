#!/bin/sh
# OMH bootstrap installer (ADR 0036). POSIX sh; stateless.
#
#   curl -fsSL https://raw.githubusercontent.com/zzzhty/oh-my-harness/main/install.sh | sh
#
# Environment:
#   OMH_VERSION   tag to install or upgrade to (default: latest release)
#   OMH_HARNESS   comma-separated harness list for a fresh bootstrap (default: codex)
#   OMH_HOME      manager home (default: ~/.oh-my-harness); the clone lands at <home>/repo
#   OMH_REPO      repository URL or local path (default: the GitHub repository)
#   OMH_REF_URL   verification asset URL or local file path (default: the release's omh-<tag>.ref asset)
#   OMH_PYTHON    absolute bootstrap interpreter override
#
# The script acquires and verifies the source tree, then delegates every
# target mutation to the standalone CLI. It keeps no state and exits.
set -eu

REPO_DEFAULT='https://github.com/zzzhty/oh-my-harness'
REPO="${OMH_REPO:-$REPO_DEFAULT}"
HOME_DIR="${OMH_HOME:-$HOME/.oh-my-harness}"
CLONE="$HOME_DIR/repo"

die() { echo "install.sh: $1" >&2; exit 1; }
log() { echo "install.sh: $1" >&2; }

command -v git >/dev/null 2>&1 || die 'git is required'
command -v curl >/dev/null 2>&1 || die 'curl is required'

require_clean_tree() {
    # checkout can retain edits at the same tag (or non-conflicting edits at a
    # different tag). Ignored files can also enter the distributor's file walk.
    dirty=$(git -C "$CLONE" status --porcelain --untracked-files=all --ignored) \
        || die "cannot inspect $CLONE; leaving the checkout unchanged"
    [ -z "$dirty" ] || die "$CLONE has local changes or untracked files (including ignored files); preserve or move them outside the clone before retrying"
}
# Refuse before fetching or running any code from an existing managed clone.
if [ -d "$CLONE/.git" ]; then require_clean_tree; fi

# --- interpreter: >= 3.11 and able to seed a usable venv --------------------
# Same strategy selection as the runtime (ADR 0037): private copies first,
# symlinked seeding as the verified fallback for relocated builds (uv-managed
# CPython). Never a silently broken environment.
python="${OMH_PYTHON:-python3}"
"$python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || die "$python is older than Python 3.11"
probe=$(mktemp -d) || die 'mktemp failed'
trap 'rm -rf "$probe"' EXIT INT TERM
seed=0
for strategy in --copies --symlinks; do
    rm -rf "$probe/venv"
    if "$python" -I -B -m venv "$strategy" --without-pip "$probe/venv" 2>"$probe/err" \
            && "$probe/venv/bin/python" -c 'import json' >/dev/null 2>&1; then
        seed=1
        break
    fi
done
[ "$seed" = 1 ] || {
    tail -n 5 "$probe/err" >&2 2>/dev/null || true
    die "$python cannot seed a usable venv (private copies and symlinks both failed); set OMH_PYTHON to a standard interpreter"
}
python=$(command -v "$python") || die "cannot resolve an absolute path for $python"

# --- release ----------------------------------------------------------------
tag="${OMH_VERSION:-}"
api=${REPO#https://github.com/}
if [ -z "$tag" ]; then
    [ "$REPO" != "$api" ] || die 'OMH_VERSION is required when OMH_REPO is not a GitHub URL'
    tag=$(curl -fsSL "https://api.github.com/repos/$api/releases/latest" \
        | sed -n 's/.*"tag_name":[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
    [ -n "$tag" ] || die 'could not resolve the latest release tag'
fi
log "release: $tag"

# --- verification: pin the tag to the release ref asset ---------------------
ref_url="${OMH_REF_URL:-}"
if [ -z "$ref_url" ]; then
    [ "$REPO" != "$api" ] || die 'OMH_REF_URL is required when OMH_REPO is not a GitHub URL'
    ref_url="https://github.com/$api/releases/download/$tag/omh-$tag.ref"
fi
case "$ref_url" in
    *://*) pinned=$(curl -fsSL "$ref_url") || die "ref asset not found: $ref_url" ;;
    *) [ -f "$ref_url" ] || die "ref asset not found: $ref_url"; pinned=$(cat "$ref_url") ;;
esac
pinned=$(printf '%s' "$pinned" | tr -d '[:space:]')
[ "${#pinned}" -ge 40 ] || die "the ref asset does not hold a commit SHA: $ref_url"
# Peeled (^{}) advertisement exists for annotated tags only; a lightweight
# tag's plain ref already points at the commit. Both yield a commit SHA.
resolved=$(git ls-remote "$REPO" "refs/tags/$tag^{}" | awk '{print $1}')
[ -n "$resolved" ] || resolved=$(git ls-remote "$REPO" "refs/tags/$tag" | awk '{print $1}')
[ -n "$resolved" ] || die "tag $tag was not found in $REPO"
[ "$resolved" = "$pinned" ] || die "tag $tag resolves to $resolved but the release pins $pinned"

# --- acquire: bootstrap clone or in-place upgrade ---------------------------
mode=upgrade
if [ -e "$CLONE" ] && [ ! -d "$CLONE/.git" ]; then
    die "$CLONE exists and is not a git clone"
fi
if [ -d "$CLONE/.git" ]; then
    log "upgrading $CLONE"
    git -C "$CLONE" fetch --tags --force origin || die 'git fetch failed'
else
    mode=bootstrap
    log "cloning $REPO into $CLONE"
    staging="$HOME_DIR/.repo.clone.$$"
    rm -rf "$staging"
    mkdir -p "$HOME_DIR"
    git -c advice.detachedHead=false clone --quiet --branch "$tag" "$REPO" "$staging" \
        || { rm -rf "$staging"; die 'git clone failed'; }
    got=$(git -C "$staging" rev-parse HEAD)
    if [ "$got" != "$pinned" ]; then
        rm -rf "$staging"
        die "clone HEAD $got does not match the pinned $pinned"
    fi
    mv "$staging" "$CLONE"
fi
git -C "$CLONE" -c advice.detachedHead=false checkout --quiet "refs/tags/$tag" \
    || die "checkout $tag failed (a dirty clone fails closed)"
got=$(git -C "$CLONE" rev-parse HEAD)
[ "$got" = "$pinned" ] || die "checkout HEAD $got does not match the pinned $pinned"
require_clean_tree

# --- delegate to the standalone CLI -----------------------------------------
# Keep each persisted target's full identity. Python passes argument arrays so
# custom roots containing spaces, quotes or non-ASCII text are never split.
"$python" -B - "$CLONE" "$HOME_DIR" "$mode" "${OMH_HARNESS:-codex}" <<'PYEOF' || die 'target installation failed'
import json, subprocess, sys
from pathlib import Path

sys.stderr.reconfigure(encoding='utf-8')
clone, home, mode, harness_list = sys.argv[1:]
index = Path(home) / 'targets.json'
try:
    targets = json.loads(index.read_bytes()) if mode == 'upgrade' and index.exists() else {}
    if not isinstance(targets, dict):
        raise ValueError('expected an object')
    selected = []
    for entry in targets.values():
        if (not isinstance(entry, dict)
                or not isinstance(entry.get('harness'), str) or not entry['harness']
                or not isinstance(entry.get('skillsRoot'), str) or not entry['skillsRoot']
                or not Path(entry['skillsRoot']).is_absolute()):
            raise ValueError('expected harness and absolute skillsRoot for every target')
        selected.append((entry['harness'], entry['skillsRoot']))
except (OSError, ValueError) as error:
    sys.exit(f'cannot read target index {index}: {error}')
if not selected:
    selected = [(harness, None) for harness in harness_list.split(',') if harness]
verb = 'install' if mode == 'bootstrap' else 'refresh'
for harness, skills_root in selected:
    print(f'{verb} target: {harness}' + (f' at {skills_root}' if skills_root else ''), file=sys.stderr)
    command = [sys.executable, '-B', '-m', 'omh', verb, '--home', home,
               '--harness', harness, '--python', sys.executable]
    if skills_root is not None:
        command += ['--skills-root', skills_root]
    result = subprocess.run(command, cwd=clone)
    if result.returncode:
        sys.exit(result.returncode)
PYEOF

log "done: $tag at $CLONE"
(cd "$CLONE" && "$python" -B -m omh status --home "$HOME_DIR") || true
