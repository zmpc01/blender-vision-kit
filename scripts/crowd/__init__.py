"""scripts/crowd/ — MOVED to blender-crowd-kit.

The crowd simulation system has been forked out into a standalone repo:
    https://github.com/zmpc01/blender-crowd-kit

Per user directive (session 27, 2026-09-27):
    "as you are still building out i suggest you create this as a
    blender-crowd-kit first and then vendor into the actual blender kit
    once you reach usable milestone."

To use the crowd system:
1. Clone blender-crowd-kit:
       git clone https://github.com/zmpc01/blender-crowd-kit.git /home/sync/blender-crowd-kit
2. Install its dependencies (Blender 5.2.2 LTS + bgyss wheel):
       cd /home/sync/blender-crowd-kit && bash install.sh
3. Import from there:
       import sys
       sys.path.insert(0, "/home/sync/blender-crowd-kit")
       from scripts.crowd import CrowdProject, Population, bake, apply_to_scene

This stub will be replaced with a proper vendor pointer (git submodule
or pip-install) once blender-crowd-kit reaches the v1 milestone (M3
complete). Until then, develop crowd features in blender-crowd-kit.

See blender-agent-kit/docs/crowd_system/STATUS.md for the fork rationale
+ migration plan.
"""
raise ImportError(
    "scripts.crowd has moved to blender-crowd-kit. "
    "Clone https://github.com/zmpc01/blender-crowd-kit and add it to PYTHONPATH. "
    "See scripts/crowd/__init__.py for details."
)
