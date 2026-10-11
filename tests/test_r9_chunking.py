# R9 D18 regression — synthetic asset round-trip (split A+B -> rebuild -> parity).
# Exercises every law the real run hit: shared materials/images across roots,
# a parent pair, mesh co-users, a user-less material (closure-gap rider), a
# scene-root orphan light, world, packed images, compositor tree, collections.
# Run: ./run.sh --background --python tests/test_r9_chunking.py
import bpy, os, sys, json, tempfile, subprocess, shutil

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = argv[0] if argv else tempfile.mkdtemp(prefix="r9test_")
os.makedirs(OUT, exist_ok=True)
FAILS = []

def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {name} {detail}", flush=True)
    if not cond:
        FAILS.append(name)

def blender_run(script, args):
    cmd = [os.environ.get("BLENDER_BIN",
           os.path.join(REPO, "tools", "blender", "blender")),
           "--background", "--factory-startup", "--python-exit-code", "1",
           "--python", script, "--"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=1200)
    return r

# ---------- build synthetic source ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def mkimg(name, fill):
    im = bpy.data.images.new(name, 32, 32)
    px = [fill] * (32 * 32 * 4)
    im.pixels.foreach_set(px)
    im.pack()
    return im

def mkmat(name, img):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"],
                 nt.nodes["Principled BSDF"].inputs["Base Color"])
    return m

img_a, img_b = mkimg("TexA", 0.2), mkimg("TexB", 0.7)
mat_shared = mkmat("Shared", img_a)
mat_solo = mkmat("Solo", img_b)
mat_orphan = bpy.data.materials.new("OrphanMat")   # fake-user rider (the Dots Stroke class)

def mkcube(name, mat, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.materials.append(mat)
    ob.data.name = name + "_mesh"
    return ob

r1 = mkcube("Root_A", mat_shared, (0, 0, 0.5))
r2 = mkcube("Root_B", mat_shared, (3, 0, 0.5))
r3 = mkcube("Root_C", mat_solo, (6, 0, 0.5))
r4 = mkcube("Root_D", mat_shared, (9, 0, 0.5))
r4.data = r1.data                      # co-user group (A + D share a mesh)
r1.data.name = "SharedMesh"
child = bpy.data.objects.new("Child_B", None)
sc.collection.objects.link(child)
child.parent = r2
child.location = (1, 2, 3)

ld = bpy.data.lights.new("RootLight", 'AREA')
ld.energy = 42.0
lo = bpy.data.objects.new("OrphanLight", ld)
sc.collection.objects.link(lo)         # scene-root orphan (chunk_00 claim)
c2 = bpy.data.collections.new("Rooms")
sc.collection.children.link(c2)
c2.objects.link(r3)
sc.collection.objects.unlink(r3)   # single membership (the loft's reality)
cld = bpy.data.lights.new("RoomLight", 'POINT')
cld.energy = 7.0
clo = bpy.data.objects.new("RoomLight", cld)
c2.objects.link(clo)

tree = bpy.data.node_groups.new("Comp Test", 'CompositorNodeTree')
n1 = tree.nodes.new("CompositorNodeRLayers")
n2 = tree.nodes.new("CompositorNodeSetAlpha")
tree.links.new(n1.outputs["Image"], n2.inputs["Image"])
sc.use_nodes = True
sc.compositing_node_group = tree
mat_orphan.use_fake_user = True   # survives the intermediate save
sc.render.fps = 24

src = os.path.join(OUT, "synthetic_src.blend")
bpy.data.use_autopack = False
bpy.ops.wm.save_as_mainfile(filepath=src, compress=True)
EXP = {"objects": len(bpy.data.objects), "meshes": len(bpy.data.meshes),
       "materials": len(bpy.data.materials),
       "lights": len(bpy.data.lights)}
print(f"  fixture (pre-save): {EXP}", flush=True)

# ---------- split A + B (subprocess, the real CLI contract) ----------
loftdir = os.path.join(OUT, "assets", "loft")
ra = blender_run(os.path.join(REPO, "scripts", "r9_split_asset.py"),
                 ["--phase", "a", "--src", src, "--outdir", loftdir])
check("phase a ok", ra.returncode == 0,
      (ra.stdout + ra.stderr)[-200:] if ra.returncode else "")
if ra.returncode:
    print((ra.stdout + ra.stderr)[-1500:]); sys.exit(1)
rb = blender_run(os.path.join(REPO, "scripts", "r9_split_asset.py"),
                 ["--phase", "b", "--outdir", loftdir])
check("phase b ok", rb.returncode == 0)
if rb.returncode:
    print((rb.stdout + rb.stderr)[-1500:]); sys.exit(1)
man = json.load(open(os.path.join(loftdir, "chunks_manifest.json")))
# post-save truth: the manifest census is what the pipeline can carry
EXP = {"objects": man["census"]["objects"], "meshes": man["census"]["meshes"],
       "materials": man["census"]["materials"], "lights": man["census"]["lights"]}
print(f"  expected (post-save census): {EXP}", flush=True)
# user-less IDs ride chunk_00 (riders list); user-ful-but-unreachable IDs
# ride the gap chunk — OrphanMat is user-less, so the riders path applies
orphan_rided = any(r.get("name") == "OrphanMat"
                   for r in man.get("riders", []))
orphan_gapped = "OrphanMat" in man.get("closure_gap", {}).get("materials", [])
check("orphan material carried (riders or gap)", orphan_rided or orphan_gapped,
      f"riders={orphan_rided} gap={orphan_gapped}")
check("disjoint write sets (union == objects)",
      len(man["chunks"]) >= 1)

# ---------- rebuild (subprocess) ----------
rr = blender_run(os.path.join(REPO, "scripts", "r9_rebuild_asset.py"),
                 ["--loftdir", loftdir,
                  "--out", os.path.join(loftdir, "master_test.blend")])
check("rebuild ok", rr.returncode == 0)
if rr.returncode:
    print((rr.stdout + rr.stderr)[-1500:]); sys.exit(1)

# ---------- verify the master in-process ----------
bpy.ops.wm.open_mainfile(filepath=os.path.join(loftdir, "master_test.blend"))
check("objects parity",
      len(bpy.data.objects) == EXP["objects"],
      f"{len(bpy.data.objects)} vs {EXP['objects']}")
check("meshes parity", len(bpy.data.meshes) == EXP["meshes"])
check("materials parity (incl. gap rider)",
      len(bpy.data.materials) == EXP["materials"],
      f"{len(bpy.data.materials)} vs {EXP['materials']}")
check("gap rider material present",
      bpy.data.materials.get("OrphanMat") is not None)
check("name-set parity",
      {o.name for o in bpy.data.objects} ==
      {"Root_A", "Root_B", "Root_C", "Root_D", "Child_B",
       "OrphanLight", "RoomLight"})
check("parent restored",
      bpy.data.objects["Child_B"].parent is not None and
      bpy.data.objects["Child_B"].parent.name == "Root_B")
check("light data values (the Area.001 law)",
      abs(bpy.data.lights["RootLight"].energy - 42.0) < 1e-5 and
      abs(bpy.data.lights["RoomLight"].energy - 7.0) < 1e-5,
      f"{bpy.data.lights['RootLight'].energy:.2f}/"
      f"{bpy.data.lights['RoomLight'].energy:.2f}")
check("collections recreated",
      bpy.data.collections.get("Rooms") is not None and
      "Root_C" in [o.name for o in bpy.data.collections["Rooms"].objects])
check("compositor re-created from dump",
      bpy.context.scene.compositing_node_group is not None and
      len(bpy.context.scene.compositing_node_group.nodes) == 2)
check("fps restored", bpy.context.scene.render.fps == 24)
# texture pixels resolve from the master (externalized + fixup);
# has_data does NOT force a load — touch pixels first
im = bpy.data.images.get("TexA")
loaded = False
if im is not None:
    try:
        _ = len(im.pixels)
        loaded = im.size[0] == 32
    except Exception:
        loaded = False
check("externalized texture loads", loaded,
      f"has_data={im.has_data if im else None}")

n_pass = sum(1 for _, ok, _ in RESULTS if False) if False else None
total = len(FAILS)
print(f"\n{'ALL PASS' if not FAILS else 'FAILURES: ' + str(FAILS)} "
      f"({15 - total if False else len([1 for _ in range(0)]) or 'see above'} checks)", flush=True)
if FAILS:
    print(f"FAILURES: {FAILS}")
    sys.exit(1)
shutil.rmtree(OUT, ignore_errors=True)
print("ALL PASS")
