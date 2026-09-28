#!/usr/bin/env bash
# run.sh — thin alias for scripts/blrun.sh (equivalent invocation).
# blrun.sh's defaults are repo-relative and relocatable (see its header),
# so both entry points behave identically in a normal checkout. run.sh
# exists as a belt-and-braces alias that also honors pre-set BLENDER_BIN /
# BLENDER_HOME / BLENDER_KIT_LIBS env vars. Either entry point is fine —
# never call the blender binary directly.
#
# Special mode (no Blender needed):
#   bash run.sh --scope-check
#     Runs tests/test_kit_scope.py — the kit-scope guard. MANDATORY before
#     any commit that adds files (see AGENTS.md two-repo contract).
REPO="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "--scope-check" ]; then
    exec python3 "$REPO/tests/test_kit_scope.py" "${2:-}"
fi

export BLENDER_BIN="${BLENDER_BIN:-$REPO/tools/blender/blender}"
export BLENDER_HOME="${BLENDER_HOME:-$REPO/.blender-home}"
export BLENDER_KIT_LIBS="${BLENDER_KIT_LIBS:-$REPO/tools/local-libs/usr/lib/x86_64-linux-gnu}"
exec "$REPO/scripts/blrun.sh" "$@"
