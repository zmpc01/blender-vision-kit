"""_fixture_fbx_patch.py — FBX platform-convention patch (structured).

Reproduces the Mixamo/RH-canvas file convention from a Blender-authored
FBX round trip, so the module's default-settings import lands the
platform laws: obj scale ~0.01, obj rot X ~+90, figure upright, hips
location fcurve values raw centimetres, fps 30.

  GlobalSettings : CustomFrameRate -> 30, TimeMode -> 14 (30fps)
  armature node  : Lcl Rotation (-90 bake) -> 0, Lcl Scaling (x100 bake) -> 1
  bone nodes     : Lcl Translation (x,y,z)m -> (x, z, -y) * 100  [Y-up cm]
                   Lcl Rotation eul -> R_x(-90) @ eul (XYZ euler)
  anim curves    : T values remap+cm per key; R values quat-remapped

Mechanics: parse_fbx (namedtuple tree) -> mutable encode_bin.FBXElem
tree (type-preserving) -> in-place mutation -> encode_bin.write.
"""
import math
import os
import sys
import types
import importlib.util

from mathutils import Quaternion, Euler

DEG = math.pi / 180.0

_FBXIO = None


def _load_fbxio():
    """Load the Blender dist's io_scene_fbx parse/encode modules as a
    synthetic package (the addon __init__ imports bpy — unavailable in
    system python, and not needed by these four modules)."""
    global _FBXIO
    if _FBXIO is not None:
        return _FBXIO
    bases = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '..', 'tools', 'blender', '5.2', 'scripts',
                     'addons_core', 'io_scene_fbx'),
    ]
    pkg = types.ModuleType('fbxio')
    pkg.__path__ = []
    sys.modules['fbxio'] = pkg
    for m in ('data_types', 'fbx_utils_threading', 'parse_fbx', 'encode_bin'):
        loaded = False
        for base in bases:
            p = os.path.join(base, m + '.py')
            if os.path.isfile(p):
                spec = importlib.util.spec_from_file_location(f'fbxio.{m}', p)
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f'fbxio.{m}'] = mod
                spec.loader.exec_module(mod)
                loaded = True
                break
        if not loaded:
            raise ImportError(f'fbxio.{m} not found under {bases}')
    from fbxio import parse_fbx, encode_bin  # noqa
    _FBXIO = (parse_fbx, encode_bin)
    return _FBXIO


_ADD_SINGLE = {
    ord('Z'): 'add_int8', ord('Y'): 'add_int16', ord('B'): 'add_bool',
    ord('C'): 'add_char', ord('I'): 'add_int32', ord('L'): 'add_int64',
    ord('F'): 'add_float32', ord('D'): 'add_float64',
    ord('R'): 'add_bytes', ord('S'): 'add_string',
}
_ADD_ARRAY = {
    ord('i'): 'add_int32_array', ord('l'): 'add_int64_array',
    ord('f'): 'add_float32_array', ord('d'): 'add_float64_array',
    ord('b'): 'add_bool_array', ord('c'): 'add_byte_array',
}


def _to_mutable(el, encode_bin):
    """parse_fbx namedtuple -> encode_bin.FBXElem (type-preserving).
    S/R values are stored RAW (no length prefix) — patching operates on
    clean values; _finalize_prefix re-prefixes before encode (the writer
    serializes S/R verbatim: the prefix must be IN the value)."""
    e = encode_bin.FBXElem(el.id)
    for v, t in zip(el.props, el.props_type):
        t = ord(t) if isinstance(t, str) else t
        if t in (ord('S'), ord('R')):
            e.props.append(v)
            e.props_type.append(t)
        elif t in _ADD_SINGLE:
            getattr(e, _ADD_SINGLE[t])(v)
        elif t in _ADD_ARRAY:
            getattr(e, _ADD_ARRAY[t])(v)
        else:
            raise ValueError(f'unknown FBX prop type {t!r}')
    for c in el.elems:
        e.elems.append(_to_mutable(c, encode_bin))
    return e


def _finalize_prefix(el):
    """Prefix every S/R prop value with its u32 length (verbatim-write
    convention), exactly once."""
    from struct import pack
    for i, t in enumerate(el.props_type):
        if t in (ord('S'), ord('R')):
            v = el.props[i]
            el.props[i] = pack('<I', len(v)) + v
    for c in el.elems:
        _finalize_prefix(c)


def _find(el, name):
    for c in el.elems:
        if c.id == name:
            return c
    return None


def _props(el):
    for c in el.elems:
        if c.id == b'Properties70':
            return c
    return None


def _set_prop(p70, name, values):
    """REPLACE an existing P record's tail values in place (same record
    count — structure-safe; the type/label codes stay untouched). New
    values are PACKED per the slot's existing type code (the writer
    requires every prop value to be bytes)."""
    from struct import pack
    codes = {'Z': '<b', 'Y': '<h', 'B': '<?', 'C': '<c', 'I': '<i',
             'L': '<q', 'F': '<f', 'D': '<d'}
    for q in p70.elems:
        if q.props and q.props[0] == name:
            n = len(q.props)
            tail = n - len(values)
            new_vals = []
            for v, t in zip(values, q.props_type[tail:]):
                t = chr(t) if isinstance(t, int) else t
                if t in codes:
                    new_vals.append(pack(codes[t], v))
                else:
                    raise ValueError(f'unpackable type {t!r} on {name!r}')
            q.props = list(q.props[:tail]) + new_vals
            return True
    raise KeyError(f'P record {name!r} not found (replace-only patch)')


def _rot_remap(eul_deg):
    """Blender-local euler (deg, XYZ) -> file Y-up euler (deg, XYZ)."""
    q = Euler([a * DEG for a in eul_deg], 'XYZ').to_quaternion()
    q_pre = Quaternion((1.0, 0.0, 0.0), -90.0 * DEG)
    e = (q_pre @ q).to_euler('XYZ')
    return [math.degrees(a) for a in e]


def _t_remap_rest(v):
    """(x,y,z) metres Blender-local -> (x, z, -y) file Y-up METRES.
    The armature node's Lcl Scaling (x100) magnifies these into the
    cm-denominated armature space; the object's 0.01 reads them back
    as world metres (the platform law's 'object scale carries the
    conversion')."""
    x, y, z = v
    return [x, z, -y]


def _t_remap_curve(v):
    """Curve values: same axis map, x100 — the raw-CENTIMETRE law
    (law 5): hips location fcurves stay raw cm post-import."""
    x, y, z = v
    return [x * 100.0, z * 100.0, -y * 100.0]


def patch_tree(root, node_scale=100.0, usf=100.0, rest_mode='m_yup',
               node_rot=0.0, curve_x100=True):
    """Platform-convention patch, RECIPE-PARAMETERIZED. The calibration
    (main) searches the recipe grid against the 9-law oracle and pins
    the winner — no hand-deduced constants.

    rest_mode: 'm_yup' (meters, Y-up mapped) | 'cm_yup' (x100) |
               'm_zup' (Blender-native values, no axis map)."""
    objs = _find(root, b'Objects')
    assert objs is not None, 'no Objects element'

    # ---- fps + unit laws ----
    gs = _find(root, b'GlobalSettings')
    p70 = _props(gs)
    _set_prop(p70, b'CustomFrameRate', [30.0])
    _set_prop(p70, b'TimeMode', [14])
    _set_prop(p70, b'UnitScaleFactor', [usf])
    _set_prop(p70, b'OriginalUnitScaleFactor', [usf])
    if node_rot:
        _set_prop(p70, b'UpAxis', [1])
        _set_prop(p70, b'UpAxisSign', [1])
        _set_prop(p70, b'FrontAxis', [2])
        _set_prop(p70, b'FrontAxisSign', [1])
        _set_prop(p70, b'CoordAxis', [0])
        _set_prop(p70, b'CoordAxisSign', [1])

    arm_node = None
    bone_nodes = {}
    for c in objs.elems:
        if c.id == b'Model' and c.props:
            nm = c.props[1]
            if isinstance(nm, bytes):
                base = nm.split(b'\x00\x01')[0]
                if base == b'FixtureArm':
                    arm_node = c
                elif base.startswith(b'mixamorig:'):
                    bone_nodes[base] = c
    assert arm_node is not None, 'armature node not found'

    # ---- armature node: strip the rotation bake, carry the cm<->m ----
    # redistribution at the node: the importer inverts the armature
    # node's scale onto the OBJECT (obj.scale = 1/Lcl Scaling) and
    # magnifies the armature-space data by it — node 100 gives the
    # platform's 0.01 object-scale law with cm armature space.
    ap = _props(arm_node)
    _set_prop(ap, b'Lcl Rotation', [node_rot, 0.0, 0.0])
    _set_prop(ap, b'Lcl Scaling', [node_scale, node_scale, node_scale])

    # ---- bone rest transforms: Y-up cm re-authoring ----
    from struct import pack
    for base, node in bone_nodes.items():
        p = _props(node)
        if p is None:
            continue
        for q in p.elems:
            if not q.props:
                continue
            nm = q.props[0]
            vals = [v for v in q.props[3:] if isinstance(v, (int, float))]
            if nm == b'Lcl Translation' and len(vals) >= 3:
                if rest_mode == 'cm_yup':
                    mapped = _t_remap_curve(vals[:3])
                elif rest_mode == 'm_yup':
                    mapped = _t_remap_rest(vals[:3])
                else:                      # 'm_zup': Blender-native values
                    mapped = list(vals[:3])
                q.props = list(q.props[:len(q.props) - 3]) \
                    + [pack('<d', v) for v in mapped]
            elif nm == b'Lcl Rotation' and len(vals) >= 3:
                # T-pose is POSITION-defined; bone node rotations must be
                # ZERO (any per-bone rest rotation compounds down the
                # 65-node chain and folds the figure — the grid search
                # proved it: every remapped variant collapsed). Rolls
                # are auto-derived on import (automatic_bone_orientation).
                q.props = list(q.props[:len(q.props) - 3]) \
                    + [pack('<d', 0.0), pack('<d', 0.0), pack('<d', 0.0)]

    # ---- animation curves (via OP connections) ----
    conns = _find(root, b'Connections')
    models_by_uid = {}
    for c in objs.elems:
        if c.id == b'Model' and c.props:
            models_by_uid[c.props[0]] = c
    cn_by_uid = {}
    for c in objs.elems:
        if c.id == b'AnimationCurveNode' and c.props:
            cn_by_uid[c.props[0]] = c

    chan_of_curve = {}     # curve uid -> (cn uid, b'X'|b'Y'|b'Z')
    target_of_cn = {}      # cn uid -> (bone base, b'T'|b'R')
    for c in (conns.elems if conns else []):
        if c.id != b'C' or len(c.props) < 4 or c.props[0] != b'OP':
            continue
        child, parent, prop = c.props[1], c.props[2], c.props[3]
        if prop in (b'd|X', b'd|Y', b'd|Z') and child in cn_by_uid:
            chan_of_curve[child] = (parent, prop[-1:])
        elif prop in (b'Lcl Translation', b'Lcl Rotation') \
                and child in cn_by_uid and parent in models_by_uid:
            nm = models_by_uid[parent].props[1]
            if isinstance(nm, bytes):
                bone = nm.split(b'\x00\x01')[0]
                kind = b'T' if prop == b'Lcl Translation' else b'R'
                target_of_cn[child] = (bone, kind)

    groups = {}
    for c in objs.elems:
        if c.id != b'AnimationCurve' or not c.props:
            continue
        link = chan_of_curve.get(c.props[0])
        if link is None:
            continue
        tgt = target_of_cn.get(link[0])
        if tgt is None:
            continue
        kts = kvf = None
        for e2 in c.elems:
            if e2.id == b'KeyTime':
                kts = e2.props[0]
            elif e2.id == b'KeyValueFloat':
                kvf = e2.props[0]
        if kts is None or kvf is None:
            continue
        groups.setdefault(tgt, {})[link[1]] = (kts, kvf)

    n_remapped_t = n_remapped_r = 0
    for (bone, kind), chans in groups.items():
        if kind == b'T' and len(chans) == 3:
            ls = [chans[b'X'][1], chans[b'Y'][1], chans[b'Z'][1]]
            if not (len(ls[0]) == len(ls[1]) == len(ls[2])):
                continue                      # unaligned keys: skip honestly
            for i in range(len(ls[0])):
                x, y, z = ls[0][i], ls[1][i], ls[2][i]
                nx, ny, nz = _t_remap_curve((x, y, z))
                ls[0][i], ls[1][i], ls[2][i] = nx, ny, nz
            n_remapped_t += 1
        elif kind == b'R' and len(chans) == 3:
            xs, ys, zs = chans[b'X'][1], chans[b'Y'][1], chans[b'Z'][1]
            if not (len(xs) == len(ys) == len(zs)):
                continue
            for i in range(len(xs)):
                ex, ey, ez = _rot_remap((xs[i], ys[i], zs[i]))
                xs[i], ys[i], zs[i] = ex, ey, ez
            n_remapped_r += 1

    # ---- purge the ARMATURE NODE's baked object curves ----
    # The exporter animates the object node even when static; the baked
    # curves carry the (-90, x100) bake and OVERRIDE the patched P
    # records at import (the object re-reads them at frame 1). The node
    # is identity by law — its curves and connections must GO.
    arm_uid = arm_node.props[0]
    arm_cn_uids = set()
    for cn_uid, (bone, kind) in target_of_cn.items():
        if bone == b'FixtureArm':
            arm_cn_uids.add(cn_uid)
    if arm_cn_uids:
        objs.elems = [c for c in objs.elems
                      if not (c.id in (b'AnimationCurveNode',
                                       b'AnimationCurve')
                              and (c.props[0] in arm_cn_uids
                                   or chan_of_curve.get(c.props[0],
                                                        (None,))[0]
                                   in arm_cn_uids))]
        if conns is not None:
            conns.elems = [c for c in conns.elems
                           if not (len(c.props) >= 3
                                   and (c.props[1] in arm_cn_uids
                                        or c.props[2] in arm_cn_uids))]

    return root, {'t_curves': n_remapped_t, 'r_curves': n_remapped_r,
                  'bones': len(bone_nodes)}


def patch_file(path, **recipe):
    """parse -> convert -> patch(recipe) -> finalize -> encode."""
    parse_fbx, encode_bin = _load_fbxio()
    root_nt, version = parse_fbx.parse(path)
    root = _to_mutable(root_nt, encode_bin)
    root, stats = patch_tree(root, **recipe)
    _finalize_prefix(root)
    encode_bin.write(path, root, version)
    return stats
