#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
echo "script_dir: ${script_dir}"
pushd "${script_dir}/.."
echo "Running tests from $(pwd)"
pytest "$@"
popd
