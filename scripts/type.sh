#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
pushd "${script_dir}/.."
echo "Running type checks from $(pwd)"
pyright "$@"
popd
