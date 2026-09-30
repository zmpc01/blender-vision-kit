#!/usr/bin/env bash
# install.sh — reprovision the Blender agent kit from scratch.
#
# Downloads Blender 4.5 LTS (supported until July 2027), extracts libEGL.so.1
# from .deb files (no root needed), and pre-warms the EEVEE shader cache.
#
# Idempotent: safe to re-run; skips already-installed components.
#
# Env vars:
#   BLENDER_KIT_ROOT  Root dir (default: this repo's checkout dir)
#   BLENDER_VERSION   Blender version to install (default: 5.2.2 LTS — supported
#                     until July 2028; the kit's compat shim also supports 4.5.x)
#
set -euo pipefail

ROOT="${BLENDER_KIT_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
BLENDER_VERSION="${BLENDER_VERSION:-5.2.2}"
# tarball URL pattern: Blender mirrors use Blender<MAJOR.MINOR>/blender-<ver>-linux-x64.tar.xz
BL_MAJOR_MINOR="$(echo "$BLENDER_VERSION" | cut -d. -f1,2)"
BL_TARBALL="blender-${BLENDER_VERSION}-linux-x64.tar.xz"
BL_URL="https://download.blender.org/release/Blender${BL_MAJOR_MINOR}/${BL_TARBALL}"

TOOLS_DIR="$ROOT/tools"
SCRIPTS_DIR="$ROOT/scripts"
LOCAL_LIBS="$TOOLS_DIR/local-libs/usr/lib/x86_64-linux-gnu"

# .deb packages — pinned versions known to work on Debian 13 (trixie)
# NOTE: libegl1 comes from the libglvnd source package (pool/main/libg/libglvnd/),
# not pool/main/libe/libegl1/ — the old path 404s after pool reorg.
LIBEGL1_DEB="libegl1_1.7.0-1+b2_amd64.deb"
LIBEGL_MESA_DEB="libegl-mesa0_25.0.7-2+deb13u1_amd64.deb"
LIBEGL1_URL="http://deb.debian.org/debian/pool/main/libg/libglvnd/${LIBEGL1_DEB}"
LIBEGL_MESA_URL="http://deb.debian.org/debian/pool/main/m/mesa/${LIBEGL_MESA_DEB}"

echo "[install] ROOT=$ROOT"
echo "[install] BLENDER_VERSION=$BLENDER_VERSION"
echo "[install] BL_URL=$BL_URL"

mkdir -p "$TOOLS_DIR" "$SCRIPTS_DIR" "$ROOT/output" "$ROOT/download" "$ROOT/.blender-home"

# ----------------------------------------------------------------------------
# 1. Blender binary
# ----------------------------------------------------------------------------
if [[ -x "$TOOLS_DIR/blender/blender" ]] && \
   "$TOOLS_DIR/blender/blender" --version 2>/dev/null | head -1 | grep -q "$BLENDER_VERSION"; then
    echo "[install] Blender $BLENDER_VERSION already installed at $TOOLS_DIR/blender/blender"
else
    echo "[install] Downloading Blender $BLENDER_VERSION..."
    cd "$TOOLS_DIR"
    # D11 (vision-kit): single-stream downloads stall in this sandbox
    # (measured: 0% for minutes; the repo's own chunked_dl.sh assembled
    # 383MB in ~20s via 16 parallel ranged chunks). Try single-stream with
    # a stall watchdog; on stall/failure fall back to chunked_dl.sh.
    BL_SIZE="$(curl -sIL --max-time 20 "$BL_URL" | grep -i content-length | tail -1 | tr -d '\r' | awk '{print $2}')"
    if [[ -n "$BL_SIZE" ]] && curl -fL --retry 3 --speed-time 30 --speed-limit 20000 \
         -o "$BL_TARBALL" "$BL_URL" 2>/dev/null \
         && [[ "$(stat -c%s "$BL_TARBALL" 2>/dev/null || echo 0)" = "$BL_SIZE" ]]; then
        echo "[install] single-stream download complete (${BL_SIZE} bytes)"
    else
        echo "[install] single-stream stalled/failed — falling back to chunked_dl.sh"
        if [[ -z "$BL_SIZE" ]]; then
            echo "[install] ERROR: couldn't read Content-Length from $BL_URL" >&2
            exit 1
        fi
        bash "$TOOLS_DIR/chunked_dl.sh" "$BL_URL" "$BL_TARBALL" "$BL_SIZE"
    fi
    echo "[install] Extracting..."
    tar xf "$BL_TARBALL"
    ln -sfn "blender-${BLENDER_VERSION}-linux-x64" blender
    rm -f "$BL_TARBALL"
    echo "[install] Blender installed: $TOOLS_DIR/blender/blender"
    "$TOOLS_DIR/blender/blender" --version | head -1
fi

# ----------------------------------------------------------------------------
# 2. libEGL.so.1 (for EEVEE_NEXT — extracted from .deb files, no root)
# ----------------------------------------------------------------------------
if [[ -f "$LOCAL_LIBS/libEGL.so.1" ]]; then
    echo "[install] libEGL.so.1 already extracted at $LOCAL_LIBS/"
else
    echo "[install] Downloading + extracting libEGL.so.1..."
    cd "$TOOLS_DIR"
    for url in "$LIBEGL1_URL" "$LIBEGL_MESA_URL"; do
        deb="$(basename "$url")"
        if [[ ! -f "$deb" ]]; then
            curl -fL --retry 3 -o "$deb" "$url"
        fi
        dpkg-deb -x "$deb" "$TOOLS_DIR/local-libs/"
    done
    if [[ ! -f "$LOCAL_LIBS/libEGL.so.1" ]]; then
        echo "[install] ERROR: libEGL.so.1 still missing after .deb extraction" >&2
        exit 1
    fi
    echo "[install] libEGL.so.1 ready: $LOCAL_LIBS/libEGL.so.1"
fi

# ----------------------------------------------------------------------------
# 3. Pre-warm EEVEE shader cache (amortizes ~30s first-frame cost)
# ----------------------------------------------------------------------------
if [[ -x "$SCRIPTS_DIR/blrun.sh" ]]; then
    echo "[install] Pre-warming EEVEE shader cache (one-time, ~30s)..."
    "$SCRIPTS_DIR/blrun.sh" --warm-cache 2>&1 | tail -5 || \
        echo "[install] WARNING: shader cache warm-up failed (non-fatal; first EEVEE render will be slower)"
else
    echo "[install] NOTE: scripts/blrun.sh not found — skipping shader warm-up"
    echo "[install]        (this is expected if you're installing just the toolchain)"
fi

# ----------------------------------------------------------------------------
# 3b. Install Pillow into Blender's bundled Python (needed for contact sheets)
# ----------------------------------------------------------------------------
# Per session-5 worklog: blrun.sh overrides HOME to BLENDER_HOME, so
# `pip install --user Pillow` installs to the wrong place. We must install
# directly into the bundled Python's site-packages (no --user flag).
echo "[install] Installing Pillow into Blender's bundled Python..."
# Bundled python lives at tools/blender/<MAJOR.MINOR>/python/bin/python3.NN —
# glob it instead of hardcoding a version dir (was hardcoded "4.2", broke on 4.5).
BLENDER_PY="$(ls "$TOOLS_DIR"/blender/*/python/bin/python3.* 2>/dev/null | head -1 || true)"
if [[ -z "$BLENDER_PY" || ! -x "$BLENDER_PY" ]]; then
    # Try to discover the python path
    BLENDER_PY=$("$TOOLS_DIR/blender/blender" --background --python-expr "
import sys; print(sys.executable)
" 2>/dev/null | tail -1)
fi
if [[ -n "$BLENDER_PY" && -x "$BLENDER_PY" ]]; then
    # Install without --user flag (goes to bundled site-packages, persists across HOME changes)
    "$BLENDER_PY" -m pip install --quiet --no-warn-script-location Pillow 2>&1 | tail -3 || \
        echo "[install] WARNING: Pillow install failed (contact sheets will fall back to ImageMagick)"
    # Verify
    "$BLENDER_PY" -c "from PIL import Image; print('[install] Pillow', Image.__version__)" 2>&1 | grep -E '\[install\]' || true
else
    echo "[install] WARNING: couldn't find Blender's python — skipping Pillow install"
fi

# ----------------------------------------------------------------------------
# 4. Verify
# ----------------------------------------------------------------------------
echo "[install] Verifying setup..."
"$SCRIPTS_DIR/blrun.sh" --background --python-expr "
import bpy
print(f'[verify] Blender {bpy.app.version_string}')
print(f'[verify] Cycles available:', 'CYCLES' in [e.name for e in bpy.types.RenderEngine.__subclasses__() if hasattr(e, \"name\")])
" 2>&1 | grep -E '\[verify\]|\[blender\] Blender' | head -5

echo "[install] Done."
echo "[install] Next: cp scripts/scene_template.py scripts/my_scene.py && edit it"
echo "[install]       ./scripts/blrun.sh --background --python scripts/my_scene.py -- --output output/test --still 1 --quality preview"
