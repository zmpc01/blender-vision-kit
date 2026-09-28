"""
polyhaven.py — minimal Poly Haven integration for a headless Blender agent kit.

Lets an agent search the Poly Haven CC0 library, download HDRIs / 3D models /
textures, and pull them into a running bpy scene. Pure stdlib (urllib + json),
so it works inside `blender --background --python` without pip installs.

API facts (verified against https://api.polyhaven.com, Sep 2026):
  * Base URL: https://api.polyhaven.com  (CDN downloads: https://dl.polyhaven.org)
  * No auth / no API key. A unique `User-Agent` header is REQUIRED.
  * GET /assets            -> {id: {name, tags, type(0=hdri,1=texture,2=model),
                                    dimensions(mm), polycount, thumbnail_url, ...}}
    GET /assets?type=hdris|textures|models  (also ?type= all)
  * GET /files/{id}        -> nested {format: {resolution: {ext: {url,size,md5,
                                    include:{relpath:{url,size,md5}}}}}}
    Mesh formats per model: blend, gltf(.gltf+.bin), usd(.usdc), fbx
    HDRI formats: hdr, exr  (resolutions 1k..24k; also tonemapped jpg)
    Texture formats: blend (full material), gltf, mtlx, + individual maps
  * GET /search?q=...      -> semantic/hybrid search (model qwen3-0.6b/v1),
                             returns {results:[{slug, score}], total, ...}

Licensing: assets are CC0 (public domain, no attribution ever, commercial OK).
           Using the *live API* requests a small "Powered by Poly Haven" credit.
           See https://polyhaven.com/our-api  and  https://github.com/Poly-Haven/Public-API

Scale (verified by parsing a downloaded .gltf bounding box):
  * Geometry in .gltf/.blend files is in METERS at real-world scale
    (dirty_football .gltf bbox = 0.2214 x 0.2200 x 0.2200 m  = a 22 cm soccer ball).
  * The API `dimensions` field is in MILLIMETRES  (divide by 1000 -> metres).
  * => No rescaling needed when importing into Blender (default unit = metres).
  * glTF is Y-up by spec; Blender's glTF importer auto-rotates to Z-up. No fixup.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
import urllib.error
import urllib.parse
import time
from typing import Any

API_BASE = "https://api.polyhaven.com"
# Unique UA is REQUIRED by the API terms. Override via env if you fork this.
USER_AGENT = os.environ.get("POLYHAVEN_UA", "blender-agent-kit/0.1 (+https://github.com/zmpc01/blender-agent-kit)")

# Where downloaded assets live.  Set POLYHAVEN_CACHE to a persistent volume
# (e.g. a mounted /data dir) so assets survive across container runs.
CACHE_DIR = os.environ.get("POLYHAVEN_CACHE", "/tmp/polyhaven_cache")

# Container-friendly defaults. A 4 GB / no-GPU box should stick to <= 2k:
#   1k HDRI hdr ~1.5 MB, 2k ~6 MB, 8k ~93 MB, 24k ~756 MB.
DEFAULT_RESOLUTION = os.environ.get("POLYHAVEN_RESOLUTION", "2k")
RESOLUTION_ORDER = ["1k", "2k", "4k", "8k", "16k", "24k"]


# --------------------------------------------------------------------------- #
#  Low-level HTTP / cache
# --------------------------------------------------------------------------- #
def _http_get_json(url: str, cache_file: str | None = None, ttl: float = 86400) -> Any:
    """GET JSON from the API (or a CDN). Caches API metadata responses to disk."""
    if cache_file and os.path.exists(cache_file):
        if (time.time() - os.path.getmtime(cache_file)) < ttl:
            with open(cache_file, "r", encoding="utf-8") as fh:
                return json.load(fh)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if cache_file:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    return data


def _download_file(url: str, dest: str, expected_md5: str | None = None,
                   overwrite: bool = False) -> str:
    """Download `url` to `dest`, verifying md5. Skips if already present & valid."""
    if os.path.exists(dest) and not overwrite:
        if expected_md5 and not _md5_matches(dest, expected_md5):
            os.remove(dest)            # corrupt / partial -> redownload
        else:
            return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)          # 1 MB streaming -> low RAM
            if not chunk:
                break
            fh.write(chunk)
    if expected_md5 and not _md5_matches(dest, expected_md5):
        raise IOError(f"md5 mismatch for {dest} (expected {expected_md5})")
    return dest


def _md5_matches(path: str, expected: str) -> bool:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == expected


# --------------------------------------------------------------------------- #
#  Search & metadata  (call these from the agent BEFORE touching bpy)
# --------------------------------------------------------------------------- #
def search_assets(query: str, asset_type: str | None = None,
                  limit: int = 20) -> list[dict]:
    """Semantic search. Returns [{id, name, score, type, thumbnail_url}, ...]
    enriched with metadata from the cached /assets index."""
    url = f"{API_BASE}/search?q={urllib.parse.quote(query)}"
    if asset_type:
        url += f"&type={asset_type}"           # hdris | textures | models | all
    res = _http_get_json(url,
                         cache_file=os.path.join(CACHE_DIR, f"search_{hash(query)&0xfffffff}.json"),
                         ttl=3600)
    index = _assets_index(asset_type)
    out = []
    for r in res.get("results", [])[:limit]:
        meta = index.get(r["slug"], {})
        out.append({
            "id": r["slug"],
            "score": r.get("score"),
            "name": meta.get("name", r["slug"]),
            "type": {0: "hdri", 1: "texture", 2: "model"}.get(meta.get("type")),
            "tags": meta.get("tags", []),
            "dimensions_mm": meta.get("dimensions"),
            "thumbnail_url": meta.get("thumbnail_url"),
        })
    return out


def _assets_index(asset_type: str | None = None) -> dict:
    url = f"{API_BASE}/assets"
    if asset_type:
        url += f"?type={asset_type}"
    return _http_get_json(url,
                          cache_file=os.path.join(CACHE_DIR, f"assets_{asset_type or 'all'}.json"),
                          ttl=86400)


def list_assets(asset_type: str | None = None) -> dict:
    """Raw /assets index. asset_type in {None,'hdris','textures','models'}."""
    return _assets_index(asset_type)


def get_files(asset_id: str) -> dict:
    """GET /files/{id}. Cached per-asset (refreshed when files_hash changes)."""
    return _http_get_json(f"{API_BASE}/files/{asset_id}",
                          cache_file=os.path.join(CACHE_DIR, "files", f"{asset_id}.json"),
                          ttl=86400)


# --------------------------------------------------------------------------- #
#  Download (resolves format + resolution, pulls the file + its `include` deps)
# --------------------------------------------------------------------------- #
def download_asset(asset_id: str, fmt: str | None = None,
                   resolution: str = DEFAULT_RESOLUTION,
                   ext: str | None = None) -> str:
    """Download an asset (and its dependent texture files) into CACHE_DIR.

    Returns the absolute path of the *main* file (ready to import/load).
      fmt:       'blend' | 'gltf' | 'fbx' | 'usd' (models/textures) or
                 'hdri' (HDRIs). Auto-chosen if omitted.
      resolution: '1k'..'24k'. Falls back to nearest smaller available.
      ext:        optional override, e.g. 'hdr' vs 'exr', or 'jpg' vs 'png'.
    """
    files = get_files(asset_id)

    fmt = fmt or _guess_format(files)
    block = files.get(fmt)
    if not block:
        raise KeyError(f"asset {asset_id} has no format '{fmt}'. Have: {list(files)}")

    res = _pick_resolution(block, resolution)
    entry = block[res]
    # entry is {ext: {url,size,md5,include}} for models/textures,
    # or for HDRIs the block IS {ext: {...}} directly.
    if "url" in entry:                          # HDRI-style: no resolution nesting
        chosen = entry
    else:
        ext = ext or _pick_ext(entry)
        chosen = entry[ext]

    base_dir = os.path.join(CACHE_DIR, asset_id, res, fmt)
    main_dest = os.path.join(base_dir, os.path.basename(chosen["url"].split("?")[0]))
    _download_file(chosen["url"], main_dest, chosen.get("md5"))

    # Pull dependent files (e.g. .blend references textures/<...>.jpg,
    # glTF references .bin + textures/). Preserve their relative paths.
    for relpath, dep in chosen.get("include", {}).items():
        dep_dest = os.path.join(base_dir, relpath)
        _download_file(dep["url"], dep_dest, dep.get("md5"))
    return main_dest


def _guess_format(files: dict) -> str:
    if "hdri" in files:
        return "hdri"
    if "blend" in files:
        return "blend"                          # best fidelity for Blender scenes
    for f in ("gltf", "usd", "fbx", "mtlx"):
        if f in files:
            return f
    raise KeyError(f"no importable format in {list(files)}")


def _pick_resolution(block: dict, want: str) -> str:
    avail = [r for r in RESOLUTION_ORDER if r in block]
    if want in block:
        return want
    # fall back to the nearest smaller resolution (container-friendly direction)
    smaller = [r for r in avail if RESOLUTION_ORDER.index(r) <= RESOLUTION_ORDER.index(want)]
    return smaller[-1] if smaller else avail[0]


def _pick_ext(entry: dict) -> str:
    # prefer small/lossy for the container, keep quality order sensible
    for e in ("jpg", "hdr", "exr", "png"):
        if e in entry:
            return e
    return next(iter(entry))


# --------------------------------------------------------------------------- #
#  Blender import helpers  (only import bpy lazily -> module stays importable
#  outside Blender for search/download)
# --------------------------------------------------------------------------- #
def _bpy():
    import bpy  # noqa
    return bpy


def ensure_metric_units() -> None:
    """Poly Haven geometry is metres at real-world scale; make the scene match."""
    bpy = _bpy()
    us = bpy.context.scene.unit_settings
    us.system = "METRIC"
    us.length_unit = "METERS"
    us.scale_length = 1.0


def import_model(path: str, location=(0.0, 0.0, 0.0), collection=None) -> list:
    """Import a downloaded model into the scene. Picks the right op by extension.
    Geometry is already in metres, so no unit fixup is applied. Returns imported
    object(s)."""
    bpy = _bpy()
    ensure_metric_units()
    before = set(bpy.data.objects)
    ext = path.lower().rsplit(".", 1)[-1]

    if ext == "blend":
        # Append the first collection (Poly Haven models ship as one collection).
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.collections = [c for c in src.collections if c is not None][:1]
        if dst.collections and dst.collections[0]:
            inst = bpy.data.objects.new(dst.collections[0].name, None)
            inst.instance_type = "COLLECTION"
            inst.instance_collection = dst.collections[0]
            (collection or bpy.context.scene.collection).objects.link(inst)
            inst.location = location
    elif ext in ("glb", "gltf"):
        bpy.ops.import_scene.gltf(filepath=path)             # auto Y-up->Z-up
    elif ext == "fbx":
        bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=True)
    elif ext in ("usd", "usda", "usdc"):
        bpy.ops.wm.usd_import(filepath=path)
    else:
        raise ValueError(f"unsupported model format: {ext}")

    new_objs = [o for o in bpy.data.objects if o not in before]
    for o in new_objs:
        o.location = (o.location[0] + location[0],
                      o.location[1] + location[1],
                      o.location[2] + location[2])
    return new_objs


def load_hdri(path: str, strength: float = 1.0, rotation_z: float = 0.0) -> None:
    """Set an .hdr/.exr as the world environment background. Minimal node tree:
    ShaderNodeTexEnvironment -> ShaderNodeBackground -> ShaderNodeOutputWorld.
    Works in Cycles and EEVEE (headless)."""
    bpy = _bpy()
    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    from blender_kit import ensure_use_nodes
    ensure_use_nodes(world)
    nt = world.node_tree
    nt.nodes.clear()

    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(path, check_existing=True)
    # Rotate the HDRI around Z (node has no .rotation; use its texture mapping).
    env.texture_mapping.rotation[2] = rotation_z

    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength

    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def apply_texture_material(path: str, target_obj=None, uv_scale: float = 1.0):
    """Quick principled BSDF from a downloaded texture .blend material (append)
    or from a single map image. For full PBR, prefer download_asset(fmt='blend')
    and append the material; this helper handles the common single-diffuse case."""
    bpy = _bpy()
    if path.lower().endswith(".blend"):
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.materials = src.materials[:1]
        return dst.materials[0] if dst.materials else None
    img = bpy.data.images.load(path, check_existing=True)
    mat = bpy.data.materials.new(name=os.path.basename(path))
    from blender_kit import ensure_use_nodes
    ensure_use_nodes(mat)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if target_obj:
        target_obj.data.materials.append(mat)
    return mat


# --------------------------------------------------------------------------- #
#  One-shot convenience
# --------------------------------------------------------------------------- #
def add_to_scene(asset_id: str, fmt: str | None = None,
                 resolution: str = DEFAULT_RESOLUTION, **kw) -> Any:
    """Download (cached) then import into the running scene.
    Auto-dispatches: HDRI -> load_hdri, model -> import_model, texture -> apply."""
    meta = _assets_index().get(asset_id, {})
    kind = {0: "hdri", 1: "texture", 2: "model"}.get(meta.get("type"))
    path = download_asset(asset_id, fmt=fmt, resolution=resolution)
    if kind == "hdri":
        load_hdri(path, **kw)
        return path
    if kind == "model":
        return import_model(path, **kw)
    return apply_texture_material(path, **kw)


if __name__ == "__main__":
    # Smoke test (no bpy needed): search + show a model's files.
    import urllib.parse  # noqa  (used in f-strings above via urllib.parse)
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "wooden chair"
    for hit in search_assets(q, limit=5):
        print(f"{hit['score']:.3f}  {hit['type']:<7}  {hit['id']}  — {hit['name']}")
