#!/usr/bin/env sh
set -eu

default_bootstrap_repository=https://github.com/zzzhty/oh-my-harness.git
default_bootstrap_ref=main

find_bootstrap_python() {
    if [ -n "${OH_MY_HARNESS_BOOTSTRAP_PYTHON:-}" ]; then
        printf '%s\n' "$OH_MY_HARNESS_BOOTSTRAP_PYTHON"
    elif command -v python3 >/dev/null 2>&1; then
        command -v python3
    elif command -v python >/dev/null 2>&1; then
        command -v python
    else
        echo "error: Bootstrap Python not found. Set OH_MY_HARNESS_BOOTSTRAP_PYTHON or install python3." >&2
        return 1
    fi
}

resolve_script_dir() {
    script_path=
    if [ -f "$0" ]; then
        script_path=$0
    else
        script_path=$(command -v "$0" 2>/dev/null || true)
    fi
    if [ -n "$script_path" ]; then
        CDPATH= cd -- "$(dirname -- "$script_path")" 2>/dev/null && pwd
    fi
}

resolve_bootstrap_source() {
    bootstrap_repository=$default_bootstrap_repository
    bootstrap_ref=$default_bootstrap_ref
    pending_option=
    for argument do
        if [ -n "$pending_option" ]; then
            case "$pending_option" in
                repository) bootstrap_repository=$argument ;;
                ref) bootstrap_ref=$argument ;;
            esac
            pending_option=
            continue
        fi
        case "$argument" in
            --repository) pending_option=repository ;;
            --repository=*) bootstrap_repository=${argument#*=} ;;
            --ref) pending_option=ref ;;
            --ref=*) bootstrap_ref=${argument#*=} ;;
        esac
    done
    if [ -n "$pending_option" ]; then
        echo "error: --$pending_option requires a value" >&2
        return 2
    fi
    if [ -z "$bootstrap_repository" ]; then
        echo "error: repository source must not be empty" >&2
        return 2
    fi
    if [ -z "$bootstrap_ref" ]; then
        echo "error: Git ref must not be empty" >&2
        return 2
    fi
}

cleanup_bootstrap() {
    if [ -n "${bootstrap_root:-}" ] && [ -d "$bootstrap_root" ]; then
        rm -rf -- "$bootstrap_root"
    fi
}

bootstrap_python=$(find_bootstrap_python)
script_dir=$(resolve_script_dir || true)
local_installer=
if [ -n "$script_dir" ] && [ -f "$script_dir/scripts/install_oh_my_harness.py" ]; then
    local_installer=$script_dir/scripts/install_oh_my_harness.py
fi

if [ -n "$local_installer" ]; then
    exec "$bootstrap_python" "$local_installer" "$@"
fi

if ! command -v git >/dev/null 2>&1; then
    echo "error: Git not found. Install Git before running the streamed installer." >&2
    exit 1
fi

resolve_bootstrap_source "$@"
bootstrap_parent=${TMPDIR:-/tmp}
bootstrap_root=$(mktemp -d "$bootstrap_parent/oh-my-harness-install.XXXXXX")
trap cleanup_bootstrap 0
trap 'exit 129' 1
trap 'exit 130' 2
trap 'exit 143' 15

git clone \
    --depth 1 \
    --branch "$bootstrap_ref" \
    --single-branch \
    -- \
    "$bootstrap_repository" \
    "$bootstrap_root/repo"

installer=$bootstrap_root/repo/scripts/install_oh_my_harness.py
if [ ! -f "$installer" ]; then
    echo "error: cloned bootstrap source has no scripts/install_oh_my_harness.py" >&2
    exit 1
fi

installer_exit_code=0
if [ -t 1 ] && [ -r /dev/tty ]; then
    "$bootstrap_python" "$installer" "$@" </dev/tty || installer_exit_code=$?
else
    "$bootstrap_python" "$installer" "$@" </dev/null || installer_exit_code=$?
fi
cleanup_bootstrap
bootstrap_root=
exit "$installer_exit_code"
