#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
current_dir="$(pwd)"
cd "${script_dir}/.."
echo "Running type checks from $(pwd)"
pyright "$@"
cd "${current_dir}"
