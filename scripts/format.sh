#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# In CI, don't sort imports
if [[ -z "${CI:-}" ]]; then
    ruff check --select I --fix "$@" "$script_dir/../src" "$script_dir/../tests" "$script_dir/../examples"
fi
ruff format "$@" "${script_dir}/../src" "${script_dir}/../tests" "${script_dir}/../examples"

