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

# --- interpreter: >= 3.11 and able to seed a venv --copies environment ------
python="${OMH_PYTHON:-python3}"
"$python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
    || die "$python is older than Python 3.11"
probe=$(mktemp -d) || die 'mktemp failed'
trap 'rm -rf "$probe"' EXIT INT TERM
if ! "$python" -I -B -m venv --copies --without-pip "$probe/venv" 2>"$probe/err" \
        || ! "$probe/venv/bin/python" -c 'import json' >/dev/null 2>&1; then
    tail -n 5 "$probe/err" >&2 2>/dev/null || true
    die "$python cannot seed a venv --copies environment (relocated builds fail this); set OMH_PYTHON to a standard interpreter"
fi
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
    git clone --quiet --branch "$tag" "$REPO" "$staging" || { rm -rf "$staging"; die 'git clone failed'; }
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

# --- delegate to the standalone CLI -----------------------------------------
if [ "$mode" = bootstrap ]; then
    harnesses="${OMH_HARNESS:-codex}"
else
    harnesses=$("$python" - "$HOME_DIR/targets.json" <<'PYEOF'
import json, sys
from pathlib import Path
index = Path(sys.argv[1])
targets = json.loads(index.read_bytes()) if index.exists() else {}
print(' '.join(sorted({entry.get('harness') for entry in targets.values()} - {None})))
PYEOF
) || harnesses=''
    [ -n "$harnesses" ] || harnesses="${OMH_HARNESS:-codex}"
fi
old_ifs=$IFS
IFS=,
for harness in $harnesses; do
    [ -n "$harness" ] || continue
    if [ "$mode" = bootstrap ]; then verb=install; else verb=refresh; fi
    log "$verb target: $harness"
    (cd "$CLONE" && "$python" -B -m omh "$verb" --home "$HOME_DIR" --harness "$harness" --python "$python") \
        || die "omh $verb --harness $harness failed"
done
IFS=$old_ifs

log "done: $tag at $CLONE"
(cd "$CLONE" && "$python" -B -m omh status --home "$HOME_DIR") || true
