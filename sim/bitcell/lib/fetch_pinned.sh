#!/usr/bin/env bash
# Fetch the pinned gf180-sram margin extractor (by reference, not vendored) and verify its sha256.
# Usage: sim/bitcell/lib/fetch_pinned.sh        -> writes sim/build/pinned/snm_extract.py
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
commit=74ba8a621c9edab9b7a75ecb19ca7ea6771588da
want=56c044cda6ccb4190a6b159a0113f7528c7c7cf91a7f1426ba917a7398b36080
out="$repo/sim/build/pinned"; mkdir -p "$out"
gh api "repos/2AMLogic/gf180-sram/contents/sim/lib/snm_extract.py?ref=$commit" --jq .content | base64 -d > "$out/snm_extract.py"
got="$(sha256sum "$out/snm_extract.py" | cut -d' ' -f1)"
[[ "$got" == "$want" ]] || { echo "fetch_pinned: sha256 mismatch ($got != $want)" >&2; rm -f "$out/snm_extract.py"; exit 1; }
echo "fetch_pinned: snm_extract.py @ ${commit:0:12} sha256 ok"
