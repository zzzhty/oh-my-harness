#!/usr/bin/env sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ -n "${OH_MY_HARNESS_BOOTSTRAP_PYTHON:-}" ]; then
    bootstrap_python=$OH_MY_HARNESS_BOOTSTRAP_PYTHON
elif command -v python3 >/dev/null 2>&1; then
    bootstrap_python=$(command -v python3)
elif command -v python >/dev/null 2>&1; then
    bootstrap_python=$(command -v python)
else
    echo "Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install python3." >&2
    exit 1
fi

exec "$bootstrap_python" "$script_dir/scripts/install_oh_my_harness.py" "$@"
