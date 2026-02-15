#!/usr/bin/env bash
#
# Script to deploy versioned documentation using mike and optionally serve it locally.
# Usage:
#   DOCS_VERSION=1.2.3 ./sync_docs_versions.sh --serve
#
# Args and environment variables: 
#   DOCS_VERSION: Optional environment variable to specify the docs version to deploy (e.g., "1.2.3"). 
#     If not set, the script will attempt to determine the version from git tags or default to "dev".
#   --serve: Optional flag to serve the versioned docs locally after deployment.
#

set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
pushd "${script_dir}/.." >/dev/null

# Decide the version slot to deploy:
# 1) DOCS_VERSION env var (manual override)
# 2) release tag on HEAD (vX.Y.Z -> X.Y.Z)
# 3) fallback to rolling dev docs
version="${DOCS_VERSION:-}"
if [[ -z "${version}" ]]; then
  tag="$(git tag --points-at HEAD | awk '/^v[0-9]/{print; exit}')"
  if [[ -n "${tag}" ]]; then
    version="${tag#v}"
  else
    version="dev"
  fi
fi

echo "Deploying docs version ${version} with alias latest (local gh-pages)..."
mike deploy --update-aliases "${version}" latest
mike set-default latest

if [[ "${1:-}" == "--serve" ]]; then
  shift
  echo "Serving versioned docs from local gh-pages branch..."
  mike serve "$@"
fi

popd >/dev/null
