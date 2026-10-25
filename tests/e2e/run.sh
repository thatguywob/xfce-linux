#!/usr/bin/env bash
# Run the same full install/boot scenarios used by CI.
set -euo pipefail

usage() {
    echo "Usage: $0 <plain|luks> [just arguments...]"
    echo "Example: $0 plain output_dir=output xfce-linux stable"
}

case "${1:-}" in
    plain|luks) mode=$1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

cd "$(dirname "${BASH_SOURCE[0]}")/../.."
# Preserve just's variable overrides before the recipe name.
overrides=()
while [[ ${1:-} == *=* ]]; do
    overrides+=("$1")
    shift
done
if [[ $# -eq 0 ]]; then
    set -- xfce-linux stable
fi
exec just "${overrides[@]}" "${mode}-test-qemu" "$@"
