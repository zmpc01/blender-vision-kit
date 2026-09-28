# VISION WAVE 1 — friction report (T0 smoke, T1 placement circuit, T2 interior+physics)

Date: 2026-09-28. Three consumer-agent sub-agents, brief = ONLY variant AGENTS.md.
CRITICAL INFRA FINDING (all 3 agents): sub-agent Read CANNOT render PNGs in this
harness ("images not available in sub-agent context"). The ORCHESTRATOR has native
vision (verified: annotation-defect catches on look_test1-4). Waves therefore test
doc+tool surface + gate discipline; the orchestrator performs vision verification
personally. NOTE: the agents' fallback (ascii packs + gates) worked exactly as the
escalation doctrine promises — T0 shipped via packs + numbers alone.

## Deduped friction (P0/P1 first)
1. [P0][doc-gap] AGENTS.md canonical example: move_to uses "location" but op requires "target" — copying docs verbatim fails (2/3 agents hit). FIX: doc + consider alias.
2. [P1][tool-gap] apply_patch --list shows op names only; move_to/set_exposure fail with bare KeyError (add_sphere has friendly params list). Consumers guess keys (33% failed-invocation rate in T2!). FIX: --list prints params; friendly errors everywhere.
3. [P1][doc-gap] snap_z/move_to/seat_at reference param + token list undocumented in AGENTS.md (only in KB, defaults unknown). FIX: headlines.
4. [P1][tool-gap] physics_gate fix queue emits physics_settle that its own executor REFUSES on penetrating movers (self-contradiction loop). FIX: emit repair variant or document + fix.
5. [P1][doc-gap] Law 28 (audit after every change) bricks chains on furnished scenes: shipped scene_interior_room FAILS its own validator baseline (P0=4 P1=12, 17 pre-existing PENETRATING pairs). FIX: law + fail_on_penetration:false documented; audit "id" param silently non-scoping — fix or message.
6. [P1][tool-gap] physics_settle prints only PASS; documented verdict tokens (AT_REST/SETTLED/...) never on console. FIX: print per-mover verdict.
7. [P2] Validator floating msg ground-relative — suggest nearest-support + gap. FIX (cheap, actionable).
8. [P2] look VERDICT object count includes annotation layer (57 vs 6) — "objects=N (M scene + K annot)". FIX.
9. [P2] --closeup re-renders full grid (L1 budget). FIX: --angles none → closeup-only.
10. [P2] render_viewport rejects BLENDER_EEVEE_NEXT (docs vocabulary) — normalize engine id; print readiness line.
11. [P2] Quick start: scene name = script filename; --closeup batches into first look; static-scene template note.
12. [P2] place_on through interposed Rug: name the TOPMOST support (doc).
13. [P2] seat_at facing/align semantics undocumented (doc).
14. [P2] ascii_vision --auto blank panels on valid images (escalation tool; kb note).

## Doctrine validation (positive)
- T1: audit caught a REAL 25mm leg penetration invisible to any eye; layered defense held.
- T1 planted-float drill: audit pair-set missed 150mm float by design (>100mm pad) — the LOOK validator caught it. Two complementary gates, exactly as documented.
- T0: near-misread (perspective vs float) — two-column law kept the agent honest.
- T2: gate fix-queue UX understandable; REFUSED_PENETRATING messages actionable.
