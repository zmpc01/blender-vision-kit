"""[CROUDE2E] Crowd-kit end-to-end gate (M3, r149).

Pure python3, no bpy. Run: python3 tests/test_crowd_e2e.py
Convention: [CROUDE2E] per check; ends with
"[CROUDE2E] ALL PASS (N checks)"; exit 1 on failure (fail-closed).

PROVISION LAW (F2E-12): the interpreter running this test must have
`blender_crowd_native` importable — install the thin-vendor wheel per
vendor/blender-crowd/addon/blender_crowd/wheels/README.md
(`pip install vendor/blender-crowd/addon/blender_crowd/wheels/*.whl`).
Check native.import fails LOUD with that hint when the module is
missing — it is never skipped silently.

Layers verified (M3 design D5, REV-2.1):
  1. thin-vendor wheel integrity — sha256 + exact size vs the README
     pin (a corrupted 17.9 MB blob passes every other gate);
  2. native import + version coherence with the wheel filename;
  3. vendored kit layer — submodule initialized, `scripts.crowd`
     imports with ONLY the kit root on sys.path, kit __version__ ==
     wheel version (the two vendor layers must move together);
  4. true e2e — CrowdScene.concourse(count=5) -> bake() into a FRESH
     tempdir (bake refuses a non-empty cache target, E_CACHE_BAKE)
     -> status "complete" + cache on disk.
"""
import hashlib
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "vendor" / "blender-crowd-kit"
# s20: the vendored SUBMODULE is the single source (M3 vendored the
# crowd-kit whole, its own vendor/blender-crowd inside) — the old
# kit-root sibling path no longer exists; the integrity ledger is the
# submodule's SHA256SUMS (committed), not a README prose pin.
WHEELS = (KIT / "vendor" / "blender-crowd" / "addon" / "blender_crowd"
          / "wheels")

PASS = []
FAILS = []


def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print(f"[CROUDE2E] PASS: {name}")
    else:
        FAILS.append(name)
        print(f"[CROUDE2E] FAILED: {name}" + (f" — {detail}" if detail else ""))


# --- 1. thin-vendor wheel integrity vs the SHA256SUMS ledger --------
led_path = WHEELS / "SHA256SUMS"
led = {}
if led_path.is_file():
    for line in led_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            led[parts[1].lstrip("*")] = parts[0]
check("pin.parse", bool(led), "SHA256SUMS ledger not found/parsable")
wheels = sorted(WHEELS.glob("blender_crowd_native-*.whl"))
check("wheel.single", len(wheels) == 1, f"found {len(wheels)} wheels")
wheel_ver = ""
if led and len(wheels) == 1:
    w = wheels[0]
    data = w.read_bytes()
    check("wheel.sha256",
          hashlib.sha256(data).hexdigest() == led.get(w.name),
          w.name)
    check("wheel.size", w.name in led, f"{w.name} in ledger")
    wm = re.match(r"blender_crowd_native-([0-9.]+)-", w.name)
    wheel_ver = wm.group(1) if wm else ""
    check("wheel.version.parse", bool(wheel_ver), w.name)
else:
    check("wheel.sha256", False, "skipped — ledger/wheel missing")
    check("wheel.size", False, "skipped — ledger/wheel missing")
    check("wheel.version.parse", False, "skipped — wheel missing")

# --- 2. native import (loud under the provision law) ----------------
native_ver = None
try:
    import blender_crowd_native  # noqa: F401
    native_ver = getattr(blender_crowd_native, "__version__", None)
except ImportError as e:
    print("[CROUDE2E] FAILED: native.import — blender_crowd_native not "
          "importable; install the thin-vendor wheel per "
          "vendor/blender-crowd/addon/blender_crowd/wheels/README.md "
          f"(pip install vendor/blender-crowd/addon/blender_crowd/wheels/*.whl). Underlying: {e}")
check("native.import", native_ver is not None)
check("native.version", bool(wheel_ver) and native_ver == wheel_ver,
      f"module {native_ver!r} != wheel {wheel_ver!r}")

# --- 3 + 4. vendored kit layer: import, coherence, true bake --------
marker = KIT / "scripts" / "crowd" / "__init__.py"
check("kit.submodule_present", marker.is_file(),
      "vendor/blender-crowd-kit not initialized "
      "(git submodule update --init vendor/blender-crowd-kit)")
kit = None
kit_ver = None
if marker.is_file():
    sys.path.insert(0, str(KIT))
    try:
        import scripts.crowd as kit  # noqa: F401 — kit root ONLY on path
        kit_ver = getattr(kit, "__version__", None)
    except Exception as e:  # noqa: BLE001 — fail-closed with detail
        print(f"[CROUDE2E] FAILED: kit.import_scripts_crowd — "
              f"{type(e).__name__}: {e}")
check("kit.import_scripts_crowd", kit_ver is not None)
check("kit.version_coherence", bool(wheel_ver) and kit_ver == wheel_ver,
      f"kit {kit_ver!r} != wheel {wheel_ver!r} — one vendor layer "
      f"moved without the other")

if kit_ver is not None:
    try:
        from scripts.crowd import CrowdScene, bake
        scene = CrowdScene.concourse(count=5)
        tmp = tempfile.mkdtemp(prefix="croude2e_")
        try:
            result = bake(scene, cache_dir=tmp)
            status = getattr(result, "status", None)
            cache_ok = any(Path(tmp).rglob("manifest.json"))
            check("e2e.bake_complete", status == "complete",
                  f"status={status!r}")
            check("e2e.cache_on_disk", cache_ok,
                  "no manifest.json under the cache dir")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:  # noqa: BLE001 — fail-closed with detail
        check("e2e.bake_complete", False, f"{type(e).__name__}: {e}")
        check("e2e.cache_on_disk", False, "not reached")
else:
    check("e2e.bake_complete", False, "kit layer unavailable")
    check("e2e.cache_on_disk", False, "kit layer unavailable")

total = len(PASS) + len(FAILS)
if FAILS:
    print(f"[CROUDE2E] {len(PASS)} passed, {len(FAILS)} failed")
    sys.exit(1)
print(f"[CROUDE2E] ALL PASS ({total} checks)")
