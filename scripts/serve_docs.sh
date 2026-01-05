#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
pushd "${script_dir}/.." >/dev/null
# mkdocs serve --config-file "${script_dir}/../mkdocs.yml" "$@"
mkdocs serve 
popd >/dev/null
