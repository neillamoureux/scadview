#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
echo "script_dir: ${script_dir}"
pushd "${script_dir}/.."
echo "Running tests from $(pwd)"
echo "CI is ${CI:-}"

# In CI, prevent external plugin autoload (blocks pytest-qt import of Qt),
# and explicitly disable pytest-qt just in case.
if [[ -n "${CI:-}" ]]; then
  export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
  extra="-p no:pytestqt"
else
  extra=""
fi
pytest "${extra[@]}" "$@"
popd
