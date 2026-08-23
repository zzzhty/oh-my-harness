#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage: scripts/upgrade_my_codex.sh [--harness ID] [options]

Options:
  --harness ID                  Registry harness id. Defaults to the registry value (currently codex).
  --bootstrap-python PATH       Base Python used to create or refresh the tooling venv.
  --codex PATH                  Explicit Codex CLI executable. Otherwise uses CODEX_BIN, PATH, then managed installs.
  --codex-home PATH             Codex home directory. Defaults to CODEX_HOME or ~/.codex.
  --tooling-python PATH         Tooling Python used for harness helpers and Codex hooks.
  --git-marketplace-source URL  Git marketplace source. Defaults to remote.origin.url.
  --git-ref REF                 Git ref for first-time Git marketplace add. Defaults to main.
  --yes                         Confirm missing instructions creation and exact managed-stale prune plans.
  --dry-run                     Print commands without changing Codex state.
  --skip-check                  Skip the final closure check.
  -h, --help                    Show this help.
EOF
}

require_value() {
    option=$1
    value=${2-}
    if [ -z "$value" ]; then
        echo "missing value for $option" >&2
        exit 2
    fi
}

resolve_command() {
    label=$1
    value=$2
    if [ -z "$value" ]; then
        echo "$label not found" >&2
        exit 1
    fi
    if [ -f "$value" ]; then
        printf '%s\n' "$value"
        return
    fi
    resolved=$(command -v "$value" 2>/dev/null || true)
    if [ -n "$resolved" ]; then
        printf '%s\n' "$resolved"
        return
    fi
    echo "$label not found: $value" >&2
    exit 1
}

find_bootstrap_python() {
    if [ -n "${MY_CODEX_BOOTSTRAP_PYTHON:-}" ]; then
        resolve_command "Bootstrap Python" "$MY_CODEX_BOOTSTRAP_PYTHON"
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return
    fi
    if command -v python >/dev/null 2>&1; then
        command -v python
        return
    fi
    echo "Bootstrap Python not found. Set MY_CODEX_BOOTSTRAP_PYTHON or install python3." >&2
    exit 1
}

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

bootstrap_python=${MY_CODEX_BOOTSTRAP_PYTHON:-}
codex_path=
codex_home=${CODEX_HOME:-"$HOME/.codex"}
tooling_python=${MY_CODEX_PYTHON:-}
harness=
git_marketplace_source=
git_ref=
dry_run=0
skip_check=0
assume_yes=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --bootstrap-python)
            require_value "$1" "${2-}"
            bootstrap_python=$2
            shift 2
            ;;
        --bootstrap-python=*)
            bootstrap_python=${1#*=}
            shift
            ;;
        --codex)
            require_value "$1" "${2-}"
            codex_path=$2
            shift 2
            ;;
        --codex=*)
            codex_path=${1#*=}
            require_value "--codex" "$codex_path"
            shift
            ;;
        --codex-home)
            require_value "$1" "${2-}"
            codex_home=$2
            shift 2
            ;;
        --codex-home=*)
            codex_home=${1#*=}
            shift
            ;;
        --tooling-python)
            require_value "$1" "${2-}"
            tooling_python=$2
            shift 2
            ;;
        --tooling-python=*)
            tooling_python=${1#*=}
            shift
            ;;
        --harness)
            require_value "$1" "${2-}"
            harness=$2
            shift 2
            ;;
        --harness=*)
            harness=${1#*=}
            require_value "--harness" "$harness"
            shift
            ;;
        --git-marketplace-source)
            require_value "$1" "${2-}"
            git_marketplace_source=$2
            shift 2
            ;;
        --git-marketplace-source=*)
            git_marketplace_source=${1#*=}
            shift
            ;;
        --git-ref)
            require_value "$1" "${2-}"
            git_ref=$2
            shift 2
            ;;
        --git-ref=*)
            git_ref=${1#*=}
            shift
            ;;
        --dry-run)
            dry_run=1
            shift
            ;;
        --yes)
            assume_yes=1
            shift
            ;;
        --skip-check)
            skip_check=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$bootstrap_python" ]; then
    bootstrap_python=$(find_bootstrap_python)
else
    bootstrap_python=$(resolve_command "Bootstrap Python" "$bootstrap_python")
fi

if [ -z "$tooling_python" ]; then
    tooling_python="$codex_home/venvs/my-codex/bin/python"
fi
venv_path="$codex_home/venvs/my-codex"

export CODEX_HOME="$codex_home"
export MY_CODEX_ROOT="$repo_root"
export MY_CODEX_PYTHON="$tooling_python"
export MY_CODEX_TOOLING_PYTHON="$tooling_python"
export PLUGIN_VALIDATOR="${PLUGIN_VALIDATOR:-$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py}"

echo "MY_CODEX_ROOT=$MY_CODEX_ROOT"
echo "CODEX_HOME=$CODEX_HOME"
echo "MY_CODEX_PYTHON=$MY_CODEX_PYTHON"
echo "MY_CODEX_TOOLING_PYTHON=$MY_CODEX_TOOLING_PYTHON"
echo "PLUGIN_VALIDATOR=$PLUGIN_VALIDATOR"
echo "BootstrapPython=$bootstrap_python"
echo "CodexPath=${codex_path:-auto-if-required-by-harness}"
echo "Harness=${harness:-registry-default}"

cd "$repo_root"

set -- "$repo_root/scripts/bootstrap_tooling_env.py" --venv "$venv_path"
if [ "$dry_run" -eq 1 ]; then
    set -- "$@" --dry-run
fi
echo "+ $bootstrap_python $*"
"$bootstrap_python" "$@"

if [ ! -f "$MY_CODEX_PYTHON" ]; then
    echo "tooling Python is unavailable after bootstrap: $MY_CODEX_PYTHON" >&2
    if [ "$dry_run" -eq 1 ]; then
        echo "Run the wrapper without --dry-run once to create the tooling environment." >&2
    fi
    exit 1
fi

set -- "$repo_root/scripts/refresh_my_codex.py" \
    --codex-home "$CODEX_HOME" \
    --venv "$venv_path" \
    --python "$MY_CODEX_PYTHON" \
    --skip-bootstrap

if [ -n "$harness" ]; then
    set -- "$@" --harness "$harness"
fi

if [ -n "$codex_path" ]; then
    set -- "$@" --codex "$codex_path"
fi

if [ -n "$git_marketplace_source" ]; then
    set -- "$@" --git-marketplace-source "$git_marketplace_source"
fi
if [ -n "$git_ref" ]; then
    set -- "$@" --git-ref "$git_ref"
fi
if [ "$dry_run" -eq 1 ]; then
    set -- "$@" --dry-run
fi
if [ "$assume_yes" -eq 1 ]; then
    set -- "$@" --yes
fi

echo "+ $MY_CODEX_PYTHON $*"
"$MY_CODEX_PYTHON" "$@"

if [ "$dry_run" -eq 1 ] && [ "$skip_check" -eq 0 ]; then
    echo "Dry run: skipping closure check because no local state was changed."
elif [ "$skip_check" -eq 0 ]; then
    set -- "$repo_root/scripts/check_my_codex.py" \
        --codex-home "$CODEX_HOME" \
        --venv "$venv_path" \
        --python "$MY_CODEX_PYTHON"
    if [ -n "$harness" ]; then
        set -- "$@" --harness "$harness"
    fi
    if [ -n "$codex_path" ]; then
        set -- "$@" --codex "$codex_path"
    fi
    echo "+ $MY_CODEX_PYTHON $*"
    "$MY_CODEX_PYTHON" "$@"
fi
