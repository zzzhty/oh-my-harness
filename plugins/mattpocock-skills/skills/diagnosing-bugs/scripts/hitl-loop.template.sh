#!/usr/bin/env bash
# Human-in-the-loop reproduction loop.
# Copy this file, edit the steps below, and run it.
# The agent runs the script; the user follows prompts in their terminal.
#
# Usage:
#   bash hitl-loop.template.sh
#
# Capture fixed-choice observations only. Do not paste logs, credentials, or
# personal data. Sign in separately before running; this script is not a sign-in form.

set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -s -p "    [Press Enter when done] " _
  printf '\n'
}

capture_yes_no() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  while true; do
    IFS= read -r -s -p "    [y/n] " answer || return 1
    # Bash consumes LF. Strip only the CR left by a CRLF line ending.
    answer=${answer%$'\r'}
    printf '\n'
    case "$answer" in
      y|Y) printf -v "$var" '%s' yes; return ;;
      n|N) printf -v "$var" '%s' no; return ;;
      *) printf '    Enter y or n only.\n' ;;
    esac
  done
}

# --- edit below ---------------------------------------------------------

step "Open the isolated, already signed-in app."

capture_yes_no ERRORED "Click the 'Export' button. Did it throw an error?"

# --- edit above ---------------------------------------------------------

printf '\n--- Captured ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
