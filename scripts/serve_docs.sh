#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
mkdocs serve --config-file "${script_dir}/../mkdocs.yml" "$@"
