# The physics gate on a production scene (escape-previz integration)

Session 15: the physics placement gate met its first real production —
`zmpc01/blender-escape-previz` "Last Ride Out" v3.3 (453 objects,
51k faces: street + 160 zombies + hero jeep + rig actors + FX). This
doc records what the gate found, the semantics that make it usable on
productions, and the reproduction commands.

## TL;DR production laws (all regression-locked)

1. **Hidden objects are not previz content.** Productions hide rig
   machinery — escape-v3.3 keeps three zombie variant PROTOTYPE meshes
   (Zed.VarA/B/C, `hide_render=True`) at the world origin, INSIDE the
   hero jeep. The gate excludes hidden meshes from the audit, from the
   sim lanes, and from the post-sim audit (`hidden_excluded` in the
   report lists them). T5w locks this.
2. **`verify_movers` = REST-VERIFY semantics (`gate_semantics:
   "rest_verify_custom"`).** The whole-scene "nothing may overlap"
   audit CANNOT pass/fail a production: by-design overlaps everywhere
   (measured on v3.3: 324 penetrating + 105 nested pairs — occupants
   inside vehicles 55-184mm, seats through occupants, mist volumes
   enveloping the cast, parallax skyline layers 3-7m through each
   other, debris-field meshes 14x405m crossing the curb line, crowd
   interpenetration). With verify_movers, rejection comes from SIM
   INSTABILITY only: does the mover rest where it was authored? The
   full static audit stays in `report["static_audit"]` as a review
   artifact.
3. **"New penetration" means SIM-CREATED.** Post-sim pairs are
   compared against the FULL static audit: a pair already penetrating
   before the sim is by-design and never rejects; a pair the sim
   created is a defect.
4. **Assemblies are not simulable as part sets.** Verifying the jeep's
   Body+Cage+Seats together explodes (81-178m escapes): the parts
   interpenetrate BY DESIGN and bullet detonates any deep
   mover-mover overlap. Verify ONE load-bearing part (the rest is
   terrain) — and only when that part does not itself deeply
   interpenetrate its terrain (the jeep body contains its occupants:
   the sim launches it — an assembly-level limitation, recorded here
   as a known boundary).
5. **Pre-launch props are honestly NOT-AT-REST.** The barricade
   chunks (Street.BarrChunk1-4, the smash-shot debris) are authored at
   their PRE-LAUNCH poses; the production animates them. The
   rest-verify honestly REJECTS them — three ESCAPE (2.5-3.4m) and one
   TOPPLE (13.4 deg), the RoadGrid paint mesh also crossing them —
   correct information: gate questions apply to content AUTHORED AT
   REST.

## Reproduction (from a kit checkout, previz cloned beside it)

```bash
# 1. static frame-1 build of the production set (no animation/render):
cd /home/z/work/previz
bash run.sh --background --python scripts/build_escape_v33_static.py -- \
  --out output/gate_integration/escape_v33_build.blend

# 2. whole-scene audit artifact (REJECTED by design — read the taxonomy):
#    exit 0 (fail_hard false); exit 2 would mean fail_hard rejection.
cd /home/z/work/kit
bash run.sh --background --python scripts/apply_patch.py -- --patch-json \
  '{"load_blend": "<previz>/output/gate_integration/escape_v33_build.blend", \
    "mutations": [{"op": "physics_gate", "fail_hard": false, \
                   "output": "<kit-out>/gate_v33_run1.json"}]}'
# <previz> = the escape-previz checkout; <kit-out> = anywhere you keep reports.

# 3. rest-verify on authored-at-rest content (the production loop):
#    verify_movers=[...props authored at rest...] -> PASS exit 0 when
#    they rest; REJECTED exit 2 with instability_pairs when they do not.
bash run.sh --background --python scripts/apply_patch.py -- --patch-json \
  '{"load_blend": "<previz>/output/gate_integration/escape_v33_build.blend", \
    "mutations": [{"op": "physics_gate", "fail_hard": true, \
                   "verify_movers": ["Street.BarrChunk1", "Street.BarrChunk2", \
                                     "Street.BarrChunk3", "Street.BarrChunk4"], \
                   "output": "<kit-out>/gate_v33_chunks.json"}]}'
# NOTE: instability_pairs mixes TWO record shapes — static pair dicts
# (keys a/b/state/...) for sim-created overlaps and sim verdict dicts
# (keys obj/verdict/...) for ESCAPED/TOPPLED/LAUNCHED. Read by the
# "verdict" key, not by position.
```

## Tool bugs the integration caught (fixed in the same batch)

- `bpy.ops.rigidbody.objects_add` poll crash on hidden terrain
  ("cannot edit hidden object") -> hidden env exclusion in _prep.
- post-sim audit ignored the hidden set -> prototype meshes rejected a
  rest-verify they were never part of.
- custom-lane verdicts had no production semantics -> rest-verify
  semantics (law 2) + static_pen_set comparison (law 3).

## Known boundary

Assembly rest-verification (law 4's second half) is a REAL gap: a
part that by-design interpenetrates its own terrain (occupants in a
vehicle) cannot be sim-verified without a collision-group design.
Track P candidate: assembly-aware verify (parent-root grouping +
intra-assembly collision masking).
