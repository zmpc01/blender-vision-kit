# PROJECTS.md — repos that stress-tested this kit

> The kit repo carries only core tooling. Projects that use the kit live in
> their own repos and sync improvements back. This table is the provenance
> pointer: what ran, where its artifacts live, and what it gave back to the
> kit. Add a row when a new project starts.

| Project | Repo | Gave back to the kit |
|---|---|---|
| escape-previz (zombie chase, v1→v3.2) | `github.com/zmpc01/blender-escape-previz` | render-speed ladder + viewport preset (FLAT/AA-off/JPEG), per-shot freeze pipeline pattern, framing_audit + auto-fit + aim-assist, coplanarity_audit (z-fight class), flicker_probe, crowd_agents AI-sim pattern, cavity edge shading default, FXAA-on-delivery, workbench FX laws (size+strobe), delivery-git discipline (force-add download/), event-anchored recut method |
| placement-lab (R&D) | `github.com/zmpc01/placement-lab` | placement_lib + 7 patch-ops + audit_contacts, physics_place (settle/place/oracle/gate) + measured laws F1–F14, crossing-ENTERING classifier, ascii_vision R5 toolchain, vision-flow study, usability-program playbook |

Deliverables (MP4/stills/blend/glb) for the escape project are tracked in
the previz repo `download/` (tags: `v2.2`, `v3`, `v3.2`) — not here.

History note: project artifacts that predate the split (session 14,
`pre-surgery-archive` tag) remain recoverable from this repo's git history.
