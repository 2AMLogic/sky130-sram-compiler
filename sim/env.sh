#!/usr/bin/env bash
# sim/env.sh -- resolve the sky130 PDK install used by every testbench in sim/,
# check it against the pin in sim/pdk.json, and print the resolved paths.
#
# Usage (sourced, not executed):
#   source sim/env.sh
#
# Resolution order (mirrors gf180-sram sim/lib/pdk_env.sh):
#   1. SKY130_PDK_PATH (a full variant dir, e.g. .../sky130A)
#   2. PDK_ROOT + PDK (default variant from sim/pdk.json: sky130A)
#   3. common install prefixes: ~/.ciel, ~/.volare, /usr/share/pdk,
#      /usr/local/share/pdk, ~/share/pdk, /opt/pdk
#
# Sets on success (exported):
#   PDK_ROOT, PDK            -- parent dir and variant name
#   SKY130_VARIANT_DIR       -- .../sky130A
#   SKY130_MODEL_FILE        -- .../libs.tech/ngspice/sky130.lib.spice
#   SKY130_STD_LIB           -- sky130_fd_sc_hd tt_025C_1v80 liberty
#   SKY130_PDK_VERSION       -- resolved open_pdks revision
#   SKY130_PDK_PIN           -- revision pinned in sim/pdk.json
#
# On failure prints "env.sh: <NAMED_ERROR>: ..." to stderr and returns 1
# (exits 1 if executed). Named errors: PIN_FILE_MISSING, PIN_FILE_INVALID,
# PDK_NOT_FOUND, PDK_FILE_MISSING, PDK_REVISION_UNKNOWN,
# PDK_REVISION_MISMATCH, TOOL_MISSING.
#
# Provenance fields are identity only (variant + revision), never a host path.

_sky130_env_main() {
  local here pin_file pin_rev variant model_rel lib_rel root="" dir="" resolved ver=""
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  pin_file="$here/pdk.json"

  _fail() { echo "env.sh: $1: $2" >&2; return 1; }

  [[ -f "$pin_file" ]] || { _fail PIN_FILE_MISSING "$pin_file not found"; return 1; }
  command -v python3 >/dev/null || { _fail TOOL_MISSING "python3 (needed to read pdk.json)"; return 1; }
  local fields
  fields="$(python3 -I - "$pin_file" <<'PY' 2>/dev/null
import json, sys
d = json.load(open(sys.argv[1]))
print(d["open_pdks_revision"]); print(d["variant"])
print(d["model_files"]["ngspice"]); print(d["model_files"]["std_cell_liberty"])
PY
)" || { _fail PIN_FILE_INVALID "$pin_file lacks open_pdks_revision/variant/model_files or is not JSON"; return 1; }
  { read -r pin_rev; read -r variant; read -r model_rel; read -r lib_rel; } <<<"$fields"
  variant="${PDK:-$variant}"

  if [[ -n "${SKY130_PDK_PATH:-}" ]]; then
    dir="$SKY130_PDK_PATH"
  elif [[ -n "${PDK_ROOT:-}" ]]; then
    dir="$PDK_ROOT/$variant"
  else
    local c
    for c in "$HOME/.ciel" "$HOME/.volare" /usr/share/pdk /usr/local/share/pdk "$HOME/share/pdk" /opt/pdk; do
      if [[ -d "$c/$variant/libs.tech/ngspice" ]]; then root="$c"; break; fi
    done
    [[ -n "$root" ]] || { _fail PDK_NOT_FOUND "no $variant install found; set PDK_ROOT (parent of $variant/) or SKY130_PDK_PATH"; return 1; }
    dir="$root/$variant"
  fi
  [[ -d "$dir/libs.tech/ngspice" ]] || { _fail PDK_NOT_FOUND "$dir has no libs.tech/ngspice"; return 1; }

  [[ -f "$dir/$model_rel" ]] || { _fail PDK_FILE_MISSING "$model_rel"; return 1; }
  [[ -f "$dir/$lib_rel" ]] || { _fail PDK_FILE_MISSING "$lib_rel"; return 1; }

  resolved="$(cd "$dir" && pwd -P)"
  if [[ "$resolved" == */versions/* ]]; then
    ver="${resolved#*/versions/}"; ver="${ver%%/*}"
  elif [[ -f "$dir/SOURCES" ]]; then
    ver="$(sed -n 's/^open_pdks[[:space:]]\+\([0-9a-f]\{7,40\}\).*/\1/p' "$dir/SOURCES" | head -1)"
  fi
  [[ -n "$ver" ]] || { _fail PDK_REVISION_UNKNOWN "cannot determine open_pdks revision of the install (no /versions/<rev>/ in path, no SOURCES line)"; return 1; }
  [[ "$ver" == "$pin_rev" ]] || { _fail PDK_REVISION_MISMATCH "installed $ver != pinned $pin_rev (sim/pdk.json)"; return 1; }

  export PDK="$variant" SKY130_VARIANT_DIR="$dir" SKY130_MODEL_FILE="$dir/$model_rel" \
         SKY130_STD_LIB="$dir/$lib_rel" SKY130_PDK_VERSION="$ver" SKY130_PDK_PIN="$pin_rev"
  export PDK_ROOT="$(dirname "$dir")"
  echo "env.sh: PDK=$PDK PDK_ROOT=$PDK_ROOT"
  echo "env.sh: SKY130_VARIANT_DIR=$SKY130_VARIANT_DIR"
  echo "env.sh: SKY130_MODEL_FILE=$SKY130_MODEL_FILE"
  echo "env.sh: SKY130_STD_LIB=$SKY130_STD_LIB"
  echo "env.sh: SKY130_PDK_VERSION=$SKY130_PDK_VERSION (matches pin)"
}

_sky130_env_main
_sky130_env_rc=$?
unset -f _sky130_env_main _fail
if [[ $_sky130_env_rc -ne 0 ]]; then
  unset _sky130_env_rc
  return 1 2>/dev/null || exit 1
fi
unset _sky130_env_rc
