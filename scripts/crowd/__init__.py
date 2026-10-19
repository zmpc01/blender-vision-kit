"""scripts/crowd/ — VENDORED re-export of blender-crowd-kit (M9.5-9.6, r043).

The crowd simulation system lives in blender-crowd-kit, vendored here as
a git submodule at ``vendor/blender-crowd-kit/`` (pinned; see
docs/crowd_system/STATUS.md for the wheel pin and restore procedure):

    git submodule update --init --recursive vendor/blender-crowd-kit

This package then re-exports the kit's public surface. Supported usage —
package-level imports only:

    from scripts.crowd import CrowdScene, bake, attach_to_scene

    scene = CrowdScene.concourse(count=1000, seed=2026)
    result = bake(scene, cache_dir="/tmp/crowd_cache")
    attach_to_scene(bpy.context.scene, result.cache_path)

The 10 canonical kit symbols (the kit's own __all__) plus the 3 legacy
names this kit documented pre-fork (CrowdProject, Population,
apply_to_scene) are all importable from here; ``from scripts.crowd
import *`` yields exactly those 13.

How it loads: the kit is imported under a private alias parent package
(``_vendored_blender_crowd_kit``) anchored at the submodule checkout.
This is deliberate — the parent kit has its own large ``scripts``
package, and importing the vendored kit's ``scripts.*`` namespace
directly would collide with it (and silently resolve stale sibling
copies). Kit code therefore always resolves kit-canonical modules.

Known limitations:
- Submodule-level imports through THIS namespace (e.g.
  ``from scripts.crowd.bake import bake``) are NOT supported — import
  names from ``scripts.crowd`` (as above).
- Re-exported classes carry alias-qualified ``__module__``
  (``_vendored_blender_crowd_kit.crowd.…``); ``pickle.load`` of crowd
  objects in a fresh interpreter requires importing ``scripts.crowd``
  first.
- Baking requires the ``blender_crowd_native`` wheel installed in the
  running Python (the vendored kit installs it via
  ``vendor/blender-crowd-kit/scripts/setup_native.sh``); the import
  here stays native-free and bake fails with a native ImportError at
  call time if the wheel is absent.

The engine is also available to the PATH-BASED crowd engine registry
(``scene_contract.CROWD_ENGINE_PATHS`` / the exporter's --crowd-plugin):
register/point at ``<repo>/vendor/blender-crowd-kit``.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

__all__ = [
    # the vendored kit's canonical 10
    "CrowdScene",
    "bake",
    "BakeResult",
    "attach_to_scene",
    "detach_from_scene",
    "BehaviorGraph",
    "ForceField",
    "load_scenario",
    "list_scenarios",
    "cancel_bake",
    # legacy documented names (pre-fork parent API; session-27 era)
    "CrowdProject",
    "Population",
    "apply_to_scene",
    # s41 authoring dataclasses (the crowd_obstacles bridge + IR
    # round-trip consumers; kit-owned surface extension — same alias
    # load, same 13+7=20-name contract, vendor-gate pinned)
    "Blocked",
    "Walkable",
    "Destination",
    "SpawnSource",
    "ForceFieldType",
    "FalloffProfile",
    "kit_to_bgyss_project_ir",
    # s24 VK sanctioned delta (+4): the authoring types the vendored
    # kit guide's own custom-CrowdScene snippet imports — the 20-name
    # contract made that snippet ImportError (the U1 finding); gate
    # updated in lockstep (20+4=24).
    "DeterminismMode",
    "NavigationSettings",
    "PopulationDistributions",
    "FidelityProfile",
]

_ALIAS = "_vendored_blender_crowd_kit"


def _load_vendored_crowd():
    """Import the vendored kit's crowd package under a private alias.

    The alias parent's __path__ points INTO the submodule checkout, so
    every kit-internal (relative) import resolves kit-canonical files —
    never this kit's own stale top-level siblings. No sys.path
    reordering, no touching of the ``scripts`` namespace this stub is
    imported through.
    """
    kit_root = (
        Path(__file__).resolve().parents[2] / "vendor" / "blender-crowd-kit"
    )
    marker = kit_root / "scripts" / "crowd" / "__init__.py"
    if not marker.is_file():
        raise ImportError(
            "scripts.crowd vendors blender-crowd-kit as a git submodule "
            "at vendor/blender-crowd-kit/, but the submodule is not "
            "initialized.\n"
            "Fix: git submodule update --init --recursive "
            "vendor/blender-crowd-kit\n"
            f"(missing marker: {marker})"
        )
    pkg = types.ModuleType(_ALIAS)
    pkg.__path__ = [str(kit_root / "scripts")]
    pkg.__package__ = _ALIAS
    sys.modules[_ALIAS] = pkg
    try:
        return importlib.import_module(_ALIAS + ".crowd")
    except BaseException:
        # Hygiene: no partial alias state survives a failed load.
        for _k in [
            _k for _k in sys.modules
            if _k == _ALIAS or _k.startswith(_ALIAS + ".")
        ]:
            sys.modules.pop(_k, None)
        raise


_kit_crowd = _load_vendored_crowd()

CrowdScene = _kit_crowd.CrowdScene
bake = _kit_crowd.bake
BakeResult = _kit_crowd.BakeResult
attach_to_scene = _kit_crowd.attach_to_scene
detach_from_scene = _kit_crowd.detach_from_scene
BehaviorGraph = _kit_crowd.BehaviorGraph
ForceField = _kit_crowd.ForceField
load_scenario = _kit_crowd.load_scenario
list_scenarios = _kit_crowd.list_scenarios
cancel_bake = _kit_crowd.cancel_bake

CrowdProject = _kit_crowd.CrowdProject
Population = _kit_crowd.Population
apply_to_scene = _kit_crowd.apply_to_scene

# s41: authoring dataclasses (crowd_obstacles bridge + IR round-trip).
# Same alias package — resolved through the vendored kit's own crowd
# package namespace so relative imports stay kit-canonical.
import importlib as _il

_env = _il.import_module(_ALIAS + ".crowd.environment")
_irmod = _il.import_module(_ALIAS + ".crowd.kit_project_ir")
_popmod = _il.import_module(_ALIAS + ".crowd.population")
Blocked = _env.Blocked
Walkable = _env.Walkable
Destination = _env.Destination
ForceFieldType = _env.ForceFieldType
FalloffProfile = _env.FalloffProfile
SpawnSource = _popmod.SpawnSource
kit_to_bgyss_project_ir = _irmod.kit_to_bgyss_project_ir

# s24 VK sanctioned delta (+4): the authoring types the vendored kit's
# own guide imports (DeterminismMode/NavigationSettings live on the
# project module; PopulationDistributions/FidelityProfile on population)
DeterminismMode = _kit_crowd.DeterminismMode
NavigationSettings = _kit_crowd.NavigationSettings
PopulationDistributions = _kit_crowd.PopulationDistributions
FidelityProfile = _kit_crowd.FidelityProfile

__crowd_kit_version__ = getattr(_kit_crowd, "__version__", "unknown")
