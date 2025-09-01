#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ruff check "$@" "$script_dir/../src" "$script_dir/../tests" "$script_dir/../examples" 
ruff check --select I "$@" "$script_dir/../src" "$script_dir/../tests" "$script_dir/../examples" 
