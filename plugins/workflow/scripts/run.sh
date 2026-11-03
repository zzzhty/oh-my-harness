#!/bin/sh
# Invoke with: sh <harness-root>/.omh-runtime/run.sh <group> <script> [args...]
set -eu
base=$(CDPATH= cd -- "${0%/*}" && pwd)
group=${1:?runtime group required}
case "$group" in ''|*[!a-zA-Z0-9_-]*) exit 2;; esac
shift
if [ "${OMH_PYTHON+x}" = x ]; then
    python=$OMH_PYTHON
else
    IFS= read -r python < "$base/$group.python"
fi
case "$python" in /*) ;; *) echo 'Prepare a runtime or set an absolute OMH_PYTHON venv interpreter' >&2; exit 2;; esac
exec "$python" -I -B "$base/omh_runtime.py" run --binding "$base/$group.json" -- "$@"
