#!/usr/bin/env bash
set -euo pipefail

main() {
  local target=${1:-}
  if [[ -z "${target}" ]]; then
    echo "usage: ./script.sh <target>" >&2
    exit 1
  fi

  echo "processing ${target}"
}

main "$@"
