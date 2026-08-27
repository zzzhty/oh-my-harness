#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage: scripts/upgrade_oh_my_harness.sh [--harness ID] [options]

Options:
  --harness ID                  Registry harness id. Defaults to the registry value (currently codex).
  --home PATH                   Manager home. Defaults to OH_MY_HARNESS_HOME or ~/.oh-my-harness.
  --bootstrap-python PATH       Base Python used to create or refresh the tooling venv.
  --codex PATH                  Explicit Codex CLI executable. Otherwise uses CODEX_BIN, PATH, then managed installs.
  --codex-home PATH             Codex home directory. Defaults to CODEX_HOME or ~/.codex.
  --tooling-python PATH         Tooling Python used for harness helpers and Codex hooks.
  --git-marketplace-source URL  Git marketplace source. Defaults to remote.origin.url.
  --git-ref REF                 Git ref for first-time Git marketplace add. Defaults to main.
  --migrate-marketplace         Apply the registry-owned retired Codex marketplace migration.
  --migrate-from-repo PATH      Replace the exact former managed Codex AGENTS.md symlink after live confirmation.
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
    if [ -n "${OH_MY_HARNESS_BOOTSTRAP_PYTHON:-}" ]; then
        resolve_command "Bootstrap Python" "$OH_MY_HARNESS_BOOTSTRAP_PYTHON"
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
    echo "Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install python3." >&2
    exit 1
}

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

bootstrap_python=${OH_MY_HARNESS_BOOTSTRAP_PYTHON:-}
codex_path=
codex_home=${CODEX_HOME:-"$HOME/.codex"}
manager_home=${OH_MY_HARNESS_HOME:-"$HOME/.oh-my-harness"}
tooling_python=${OH_MY_HARNESS_PYTHON:-}
harness=
git_marketplace_source=
git_ref=
dry_run=0
skip_check=0
assume_yes=0
migrate_marketplace=0
migrate_from_repo=

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
        --home)
            require_value "$1" "${2-}"
            manager_home=$2
            shift 2
            ;;
        --home=*)
            manager_home=${1#*=}
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
        --migrate-marketplace)
            migrate_marketplace=1
            shift
            ;;
        --migrate-from-repo)
            require_value "$1" "${2-}"
            migrate_from_repo=$2
            shift 2
            ;;
        --migrate-from-repo=*)
            migrate_from_repo=${1#*=}
            require_value "--migrate-from-repo" "$migrate_from_repo"
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

case "$manager_home" in
    /*) ;;
    *)
        echo "manager home must be an absolute path: $manager_home" >&2
        exit 2
        ;;
esac

if [ -z "$bootstrap_python" ]; then
    bootstrap_python=$(find_bootstrap_python)
else
    bootstrap_python=$(resolve_command "Bootstrap Python" "$bootstrap_python")
fi

if [ -z "$tooling_python" ]; then
    tooling_python="$manager_home/venv/bin/python"
fi
venv_path="$manager_home/venv"

export CODEX_HOME="$codex_home"
export OH_MY_HARNESS_HOME="$manager_home"
export OH_MY_HARNESS_ROOT="$repo_root"
export OH_MY_HARNESS_PYTHON="$tooling_python"
export OH_MY_HARNESS_TOOLING_PYTHON="$tooling_python"
if [ -z "${PLUGIN_VALIDATOR:-}" ]; then
    omh_system_plugin_validator="$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py"
    omh_system_identifier_validator="$CODEX_HOME/skills/.system/plugin-creator/scripts/identifier_validation.py"
    if [ -f "$omh_system_plugin_validator" ] && [ -f "$omh_system_identifier_validator" ]; then
        PLUGIN_VALIDATOR="$omh_system_plugin_validator"
    else
        PLUGIN_VALIDATOR="$OH_MY_HARNESS_ROOT/scripts/validate_plugin.py"
    fi
fi
export PLUGIN_VALIDATOR

echo "OH_MY_HARNESS_HOME=$OH_MY_HARNESS_HOME"
echo "OH_MY_HARNESS_ROOT=$OH_MY_HARNESS_ROOT"
echo "CODEX_HOME=$CODEX_HOME"
echo "OH_MY_HARNESS_PYTHON=$OH_MY_HARNESS_PYTHON"
echo "OH_MY_HARNESS_TOOLING_PYTHON=$OH_MY_HARNESS_TOOLING_PYTHON"
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

if [ ! -f "$OH_MY_HARNESS_PYTHON" ]; then
    echo "tooling Python is unavailable after bootstrap: $OH_MY_HARNESS_PYTHON" >&2
    if [ "$dry_run" -eq 1 ]; then
        echo "Run the wrapper without --dry-run once to create the tooling environment." >&2
    fi
    exit 1
fi

set -- "$repo_root/scripts/refresh_harness.py" \
    --home "$OH_MY_HARNESS_HOME" \
    --codex-home "$CODEX_HOME" \
    --venv "$venv_path" \
    --python "$OH_MY_HARNESS_PYTHON" \
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
if [ "$migrate_marketplace" -eq 1 ]; then
    set -- "$@" --migrate-marketplace
fi
if [ -n "$migrate_from_repo" ]; then
    set -- "$@" --migrate-from-repo "$migrate_from_repo"
fi

echo "+ $OH_MY_HARNESS_PYTHON $*"
"$OH_MY_HARNESS_PYTHON" "$@"

if [ "$dry_run" -eq 1 ] && [ "$skip_check" -eq 0 ]; then
    echo "Dry run: skipping closure check because no local state was changed."
elif [ "$skip_check" -eq 0 ]; then
    set -- "$repo_root/scripts/check_harness.py" \
        --home "$OH_MY_HARNESS_HOME" \
        --codex-home "$CODEX_HOME" \
        --venv "$venv_path" \
        --python "$OH_MY_HARNESS_PYTHON"
    if [ -n "$harness" ]; then
        set -- "$@" --harness "$harness"
    fi
    if [ -n "$codex_path" ]; then
        set -- "$@" --codex "$codex_path"
    fi
    echo "+ $OH_MY_HARNESS_PYTHON $*"
    "$OH_MY_HARNESS_PYTHON" "$@"
fi
