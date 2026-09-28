#!/usr/bin/env bash
# blrun.sh — robust wrapper for headless Blender in a container.
#
# Responsibilities:
#   1. Validate Blender binary exists (clear error if not).
#   2. Start Xvfb on a free display (or reuse one already running).
#   3. Add locally-extracted libEGL.so.1 to LD_LIBRARY_PATH (EEVEE_NEXT needs it).
#   4. Set HOME to a project-local dir so Blender caches are reproducible.
#   5. Run Blender, propagate its exit code, clean up Xvfb on any exit/signal.
#   6. Prefix Blender's output with `[blender]` for log clarity.
#
# Subcommands:
#   blrun.sh --warm-cache        Pre-warm EEVEE shader cache (~30s, one-time per container)
#   blrun.sh --help              Show this help
#
# Env vars:
#   BLENDER_BIN       Path to blender binary (default: <kit>/tools/blender/blender)
#   BLENDER_DISPLAY   X display (default: :99)
#   KEEP_XVFB=1       Don't kill Xvfb on exit (for reuse across runs)
#   BLENDER_HOME      Where Blender puts caches/config (default: <kit>/.blender-home)
#   BLENDER_KIT_LIBS  Path to local-libs dir (default: <kit>/tools/local-libs/usr/lib/x86_64-linux-gnu)
#
# <kit> defaults to this script's repo root (parent of scripts/) — relocatable.
#
# Usage:
#   blrun.sh --background --python my_script.py -- --output out/ --still 1
#
set -uo pipefail   # NOT -e: we handle errors explicitly so we can clean up Xvfb.

# ----- Help -----
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    sed -n '2,/^# ----- Help/p' "$0" | sed 's/^# \?//' | head -n -2
    exit 0
fi

# ----- Defaults (relative to kit root = parent of this script's dir) -----
KIT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER_BIN="${BLENDER_BIN:-$KIT_ROOT/tools/blender/blender}"
BLENDER_DISPLAY="${BLENDER_DISPLAY:-:99}"
BLENDER_HOME="${BLENDER_HOME:-$KIT_ROOT/.blender-home}"
# Read-only checkout fallback (usability round-1/U2): a kit clone mounted
# read-only would make the default HOME dir unwritable — fall back to /tmp.
if [[ ! -w "$KIT_ROOT" && -z "${BLENDER_HOME:-}" && ! -w "$BLENDER_HOME" ]]; then
    BLENDER_HOME="/tmp/blender-home"
    echo "[blrun] kit checkout not writable — using BLENDER_HOME=$BLENDER_HOME" >&2
fi
# v3.3 previz fork (session-24 union): fall back to the sibling kit
# checkout's tools/ (this repo deliberately carries no Blender install)
if [[ ! -x "$BLENDER_BIN" && -x "/home/z/blender-agent-kit/tools/blender/blender" ]]; then
    BLENDER_BIN="/home/z/blender-agent-kit/tools/blender/blender"
    BLENDER_KIT_LIBS_FALLBACK="/home/z/blender-agent-kit/tools/local-libs/usr/lib/x86_64-linux-gnu"
fi
BLENDER_KIT_LIBS="${BLENDER_KIT_LIBS:-${BLENDER_KIT_LIBS_FALLBACK:-$KIT_ROOT/tools/local-libs/usr/lib/x86_64-linux-gnu}}"

# ----- Validate Blender binary -----
if [[ ! -x "$BLENDER_BIN" ]]; then
    echo "[blrun] ERROR: blender binary not found or not executable: $BLENDER_BIN" >&2
    echo "[blrun]        Run install.sh, or set BLENDER_BIN env var." >&2
    exit 127
fi

# ----- Compute X display file paths -----
DISPLAY_NUM="$(echo "$BLENDER_DISPLAY" | tr -d ':')"
XLOCK="/tmp/.X${DISPLAY_NUM}-lock"
XSOCKET="/tmp/.X11-unix/X${DISPLAY_NUM}"

# ----- Helper: is Xvfb already running on our display? -----
xvfb_running() {
    pgrep -f "Xvfb $BLENDER_DISPLAY " >/dev/null 2>&1
}

# ----- Handle stale lock files -----
# Case A: lock file exists but no Xvfb is running → stale, remove it
# Case B: lock file exists and Xvfb is running → reuse, leave it alone
# Case C: no lock file → clean state
if [[ -e "$XLOCK" ]] && ! xvfb_running; then
    owner="$(stat -c %U "$XLOCK" 2>/dev/null || echo unknown)"
    if ! rm -f "$XLOCK" "$XSOCKET" 2>/dev/null; then
        echo "[blrun] ERROR: stale X lock $XLOCK exists (owned by $owner) and cannot be removed." >&2
        echo "[blrun]        Try: sudo rm -f $XLOCK $XSOCKET" >&2
        exit 1
    fi
    echo "[blrun] removed stale X lock $XLOCK"
fi

# ----- Start Xvfb if needed -----
XVFB_PID=""
if ! xvfb_running; then
    mkdir -p /tmp/.X11-unix 2>/dev/null || true
    chmod 1777 /tmp/.X11-unix 2>/dev/null || true
    Xvfb "$BLENDER_DISPLAY" -screen 0 1280x720x24 -nolisten tcp \
        +extension GLX +extension RANDR &
    XVFB_PID=$!

    # Wait for the X socket to appear (the real readiness signal), with timeout.
    READY=0
    for i in {1..50}; do
        if [[ -e "$XSOCKET" ]]; then
            READY=1
            break
        fi
        # Check if Xvfb died early
        if ! kill -0 "$XVFB_PID" 2>/dev/null; then
            echo "[blrun] ERROR: Xvfb died during startup. Check /tmp for stale locks." >&2
            exit 1
        fi
        sleep 0.1
    done
    if [[ "$READY" -ne 1 ]]; then
        echo "[blrun] ERROR: Xvfb did not create $XSOCKET within 5s." >&2
        kill -9 "$XVFB_PID" 2>/dev/null || true
        exit 1
    fi
    echo "[blrun] Xvfb started on $BLENDER_DISPLAY (pid=$XVFB_PID)"
else
    echo "[blrun] reusing existing Xvfb on $BLENDER_DISPLAY"
fi

# ----- Cleanup on exit/signal -----
# Captures the exit code BEFORE running cleanup, then escalates to SIGKILL
# if SIGTERM doesn't take Xvfb down.
cleanup() {
    local rc=$?
    if [[ -n "$XVFB_PID" && -z "${KEEP_XVFB:-}" ]]; then
        kill "$XVFB_PID" 2>/dev/null || true
        # Wait briefly, then escalate to SIGKILL
        for i in {1..10}; do
            kill -0 "$XVFB_PID" 2>/dev/null || break
            sleep 0.1
        done
        kill -9 "$XVFB_PID" 2>/dev/null || true
        rm -f "$XLOCK" "$XSOCKET" 2>/dev/null || true
    fi
    exit "$rc"
}
trap cleanup EXIT INT TERM HUP

# ----- Set up environment -----
export DISPLAY="$BLENDER_DISPLAY"
export LD_LIBRARY_PATH="$BLENDER_KIT_LIBS:${LD_LIBRARY_PATH:-}"

# Project-local HOME for reproducible Blender caches/config
mkdir -p "$BLENDER_HOME/.cache/blender" "$BLENDER_HOME/.config/blender"
export HOME="$BLENDER_HOME"

# Make scripts/ importable as blender_kit
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# ----- Handle --warm-cache subcommand -----
if [[ "${1:-}" == "--warm-cache" ]]; then
    shift
    echo "[blrun] warming EEVEE shader cache (one-time, ~30s)…"
    WARM_SCRIPT="$(mktemp /tmp/blender_warm_XXXX.py)"
    cat > "$WARM_SCRIPT" <<'PY'
import bpy, sys, time
print(f"[warm] Blender {bpy.app.version_string}")
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add()
bpy.ops.object.light_add(type='SUN')
bpy.ops.object.camera_add(location=(3,-3,2), rotation=(1.1,0,0.785))
bpy.context.scene.camera = bpy.context.active_object
# Use the version-correct EEVEE engine id (4.x: BLENDER_EEVEE_NEXT, 5.x: BLENDER_EEVEE)
import blender_kit
bpy.context.scene.render.engine = blender_kit.EEVEE_ENGINE_ID
bpy.context.scene.eevee.taa_render_samples = 1
bpy.context.scene.render.resolution_x = 64
bpy.context.scene.render.resolution_y = 64
bpy.context.scene.render.filepath = '/tmp/_blender_warm.png'
t0 = time.time()
bpy.ops.render.render(write_still=True)
print(f"[warm] done in {time.time()-t0:.1f}s")
PY
    set -- --background --python "$WARM_SCRIPT"
fi

# ----- Run Blender, prefix its output, preserve exit code -----
# Pipe through sed for log clarity, use PIPESTATUS to capture Blender's exit
# (not sed's).
#
# --python-use-system-env (Blender 4.2+) makes Blender's bundled Python
# respect PYTHONPATH so scripts can `import blender_kit` from this dir.
BLRUN_OUT="$(mktemp /tmp/blrun_out_XXXXXX.log)"
BLRUN_ERR="$(mktemp /tmp/blrun_err_XXXXXX.log)"
echo "[blrun] launching: $BLENDER_BIN $* (heartbeat — if this hangs >60s, " \
     "see AGENTS.md gotcha 'EEVEE' or kill and retry; first run may be " \
     "cold-cache)" >&2
"$BLENDER_BIN" --python-use-system-env "$@" \
    2> >(tee "$BLRUN_ERR" | sed 's/^/[blender] /' >&2) \
    | tee "$BLRUN_OUT" | sed 's/^/[blender] /'
EXIT_CODE=${PIPESTATUS[0]}
# Fail-closed wrapper (round-E subject B): Blender exits 0 even when the
# script RAISED — exit codes could not gate success. A Python traceback
# in either stream means the script crashed; force the exit nonzero.
# Escape hatch: BLRUN_NO_TRACEBACK_GATE=1 (tests that intentionally
# print tracebacks).
if [[ -z "${BLRUN_NO_TRACEBACK_GATE:-}" ]] \
        && { grep -qE "Traceback \(most recent call last|IndentationError:|SyntaxError:|NameError:|TypeError:|AttributeError:" "$BLRUN_OUT" \
          || grep -qE "Traceback \(most recent call last|IndentationError:|SyntaxError:|NameError:|TypeError:|AttributeError:" "$BLRUN_ERR"; }; then
    echo "[blrun] FAIL-CLOSED: Python error in output — forcing nonzero exit" >&2
    [[ "$EXIT_CODE" -eq 0 ]] && EXIT_CODE=1
fi
rm -f "$BLRUN_OUT" "$BLRUN_ERR"
exit "$EXIT_CODE"
