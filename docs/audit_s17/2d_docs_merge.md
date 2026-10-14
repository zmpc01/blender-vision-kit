# Task 2-d — Docs/Merge consistency audit (read-only)

Scope: the tip `2c19f6c` = push-protection-redaction commit on top of merge
`2085bba` (parents: `c27b971` = FILM lane, `31d8dee` = KIT lane).
Method: read SKILL.md / HANDOFF.md / PLAN.md / AGENTS.md in full, diffed the
merge against both parents, grepped conflict markers, and verified every
AGENTS.md consumer-doc claim against argparse/exit-code/output-path code at
tip. Findings only below; the CLEAN list is at the end (final message).

Severity: P0 crash/corrupt · P1 nonexistent command/flag/exit-code or
misleading-into-silent-wrong-behavior · P2 stale claims/counts/cross-refs ·
P3 style.

---

## Findings

### F2D-1 · P1 — SKILL.md Git workflow names the WRONG remotes (upstream repo)
- **Where**: `.agents/SKILL.md:145-146` —
  `- **Repo**: github.com/zmpc01/blender-agent-kit (primary)` /
  `- **Mirror**: gitlab.com/ansgareutychisO/blender-agent-kit (backup)`
- **Reality**: `git remote -v` → origin `github.com/zmpc01/blender-vision-kit`,
  gitlab `ansgareutychisO/blender-vision-kit`. HANDOFF.md:291 also says
  `github.com/zmpc01/blender-vision-kit`. PLAN.md M0 records the fork vehicle
  ("new repo zmpc01/blender-vision-kit … upstream keeps history").
- **Why it matters**: SKILL.md is the meta-agent's operating manual. "GIT IS
  THE DISK — push to BOTH on every micro-step" aimed at the wrong repo names
  sends kit commits to the UPSTREAM blender-agent-kit repo. This is a
  silent-wrong-target instruction, not a cosmetic typo (the upstream mirror
  of this variant lives at the GitLab path but as `blender-vision-kit`, so
  even the mirror name is wrong).
- **Fix**: change both lines to `…/blender-vision-kit`. While there, note the
  origin URL currently embeds a `[REDACTED:github_token]` placeholder (see
  F2D-3) so `git push origin` cannot succeed until creds are restored.

### F2D-2 · P1 — Redaction is HALF-DONE: a live GitLab PAT is still committed in 4 helper scripts; the ".env is the token's home" claim has no in-repo substrate
- **Where** (all in the tip tree):
  - `scripts/_sess16_git_setup.sh:7` — `GL_PAT="glpat-…"`
  - `scripts/_sess16_gl_check.sh:3` — same token
  - `scripts/_sess16_gl_ensure_project.sh:3` — same token
  - `scripts/_sess16_gl_retry.sh:3` — same token
  - local `.git/config` gitlab remote URL embeds the same `glpat-…`
- **Reality vs doc**: HANDOFF.md:594-604 ("THE PUSH-PROTECTION EVENT")
  redacted only the `ghp_*` pattern (`GH_PAT="REDACTED-GITHUB-PAT-see-env"`
  in `_sess16_git_setup.sh:6` / `_sess16_gh_check.sh:3`) and declares "the
  token's home is .env; the lane must stop committing tokens". But:
  1. the GitLab PAT is a **live secret in git history on both remotes**;
  2. **no `.env` or `.env.example` exists anywhere in the repo** (checked)
     and no bootstrap doc defines its keys — the documented ".env pattern"
     is aspirational, not implemented;
  3. `scripts/_sess16_git_setup.sh:9-14` re-writes the origin URL from the
     REDACTED placeholder — running the documented "restores auth after a
     fresh clone" helper **breaks** origin (this is exactly the state of the
     local `.git/config` now).
- **Runtime impact**: none — verified no kit runtime path reads a token
  (blrun/look/apply_patch/exporter/tests are token-free; the `_sess16_*`
  helpers are ops-only; `push_both.sh` uses plain `git push`). So no P0.
- **Fix**: rotate the GitLab PAT (it is burned in both remote histories),
  move the helpers to read `${GL_PAT:?}` from the environment/.env (add
  `.env.example` with key names only), and either delete or neutralize the
  four scripts at the next docs/code touch.

### F2D-3 · P2 — HANDOFF contradicts itself about which remote is canonical (top-of-file state is stale)
- **Where**: `HANDOFF.md:5` ("HEAD on **GitLab**"), `HANDOFF.md:11-17`
  ("THE GITHUB PAT IS DEAD … GitLab carried the session … GitHub is stuck at
  e64528f") vs `HANDOFF.md:600-601` (tip addendum: "GitHub main = 2085bba
  (canonical, clean); GitLab main = the raw lane line 78a3eaf").
- **Why it matters**: the session-16 close state is the FIRST thing a fresh
  session reads and it describes the pre-event world; the authoritative
  post-redaction state sits at the very bottom. A consumer planning pushes
  from the top block will reconcile GitHub when GitHub is already canonical
  and may treat GitLab's raw PAT-carrying line (`78a3eaf`) as the thing to
  merge — which addendum 2 explicitly forbids.
- **Fix**: prepend one line to the close state: "SUPERSEDED below by
  'THE PUSH-PROTECTION EVENT' — GitHub main is now canonical (2085bba);
  do not merge GitLab's raw line." Also document that the local origin URL
  carries a redacted placeholder until the user supplies a fresh PAT.

### F2D-4 · P2 — Union merge kept the FILM lane's stale "standing kit chores" beside the KIT lane's fixes (F-TD9 + filing count)
- **Where**: `HANDOFF.md:78-82` — "The standing kit chores (unchanged):
  F-TD9 (the install.sh Pillow probe), the six older filings (F-TD1/2/3 +
  the make_material default), F-TF6 …"
- **Contradicts**: `HANDOFF.md:36-40` (same file, 40 lines up: Wave A "test_v9
  8/8: … install.sh authoritative Pillow probe + symlink heal"),
  `PLAN.md:357-359` ("Wave A kit fixes … F-TD9 + QA-R69 install.sh"),
  `docs/USABILITY_S16_session16.md:32-35`, and the code — install.sh:141-180
  (authoritative Pillow probe: BLENDER_PY override → BLENDER_BIN probe →
  tools/blender probe → newest-glob) + install.sh:88-93 (QA-R69 dangling
  symlink heal) + `blender_kit/__init__.py:516,549` (make_material pins
  Emission Color; emission kwargs = the closed make_material filing).
- **Also**: the parenthetical "(F-TD1/2/3 + the make_material default)"
  lists **four** items under the label "the **six** older filings"
  (same miscount repeated at `HANDOFF.md:579` and `PLAN.md:397`).
- **Fix**: rewrite HANDOFF.md:78-82 to the kit lane's recount — standing
  chores = F-TF6 (+ F-TG1 arrival semantics); true older-filings remainder =
  F-TD1/2/3; F-TD9 and the make_material default CLOSED (session-16).

### F2D-5 · P2 — Same contradiction inside PLAN.md's session-16 receipts
- **Where**: `PLAN.md:395-397` (film lane's receipts, merged verbatim):
  "Next-session candidates … (2) **F-TD9 + the six older filings**" — while
  `PLAN.md:357-362` (kit lane's receipts, 40 lines up) records F-TD9 FIXED in
  Wave A and "the true older-filings remainder is F-TD1/2/3", and
  `PLAN.md:341-342` records the make_material default CLOSED.
- **Why it matters**: two adjacent "next-session value order" lists disagree
  about what work remains; the film lane's list would send the next session
  to re-fix closed filings.
- **Fix**: strike "(2) F-TD9 + the six older filings" from the film-lane
  receipt block or annotate "(superseded — see the kit-quality receipt
  above)".

### F2D-6 · P2 — Battery receipt: HANDOFF points at a gitignored, nonexistent 26/26 receipt; the durable in-repo receipt shows the PRE-FIX run (20/26)
- **Where**: `HANDOFF.md:31` — "**Battery 26/26**
  (output/battery_s16/RESULTS.md)". `.gitignore:2` ignores `output/`;
  `output/battery_s16/RESULTS.md` does not exist at tip **or on disk**
  (output/ contains only this audit's dir).
- **Contradicts**: the durable copy `docs/battery_s16_results.md:39-40`
  ("**PASS: 20 / 26** … **FAIL: 6** — suites 1, 3, 4, 5, 8, 24") and its row
  25 "98 checks" for t10p (tip code has exactly **100** checks — counted:
  44 base + 42 variants + 8 leniency + 2 lunge + 3 garbage + 1 shots).
- **Assessment**: the 26/26 claim is *plausible* — every one of the six
  failures is verified fixed in code (suite 1: probe moved to
  `smoke/crowd/`; suites 3/4/5/8: `BLRUN_FORCE=1` present in all four,
  grepped; suite 24: `export_usd.py:167-168` RNA-filter) — but **no
  committed receipt evidences the post-fix run**, and the only committed
  receipt contradicts the headline number.
- **Fix**: commit the post-fix RESULTS table into
  `docs/battery_s16_results.md` (append a "re-run after Wave A/D fixes:
  26/26" section with per-suite markers), and re-point HANDOFF.md:31 at the
  docs/ path. Otherwise demote the HANDOFF claim to "26/26 after fixes
  (receipt was ephemeral; fix evidence = test_v9/t10 + per-fix commits)".

### F2D-7 · P2 — worklog.md: the merge duplicated the film lane's whole "Session 16 (main)" block
- **Where**: `worklog.md:3755` and `worklog.md:3801` — the header
  "## Session 16 (main) — GREEN LIGHT: the third film, end-to-end" appears
  twice; lines 3755-3800 ≈ 3801-3845 are identical (~46 lines) except one
  trailing blank.
- **Origin**: parent1 (`2085bba^1`) has ONE copy (line 3661), parent2 has
  none; the union merge inserted parent1's block twice (combined diff shows
  the header added; classic mis-anchored union duplication).
- **Fix**: delete the second copy (lines 3801-3845, keep one blank line).

### F2D-8 · P2 — Merge dropped the film lane's law blocks from SKILL.md (merge message says "both lanes' laws kept")
- **Where**: the merge replaced parent1's SKILL sections — "SESSION 15
  LAWS (the app lane + LAST FERRY build)", "SESSION 13/14 LAWS", "D18 ASSET
  PARTITION LAWS (session 13)", "R7/R8 addenda", "Session-5 meta",
  "Session-6/7 meta", "Session-12 meta: the vision-native FILM" — with the
  kit lane's differently-compacted blocks ("SESSION 14/15 LAWS (condensed)",
  "Session-12/13 meta (condensed)"). Parent1 had 25 `##` sections, the merge
  kept 20.
- **Concretely lost from SKILL.md** (grep-verified absent at tip; were in
  parent1 at lines 359-380):
  - the **E_InvalidRange barricade law** ("Barricade squares past the
    walkable edge = E_InvalidRange (cap at walkable−r)"),
  - "**Kit mode has NO hero-lane pushout (HERO_LANES dead data)" = the
    F-TF6 law,
  - the **tferry choke law** (the bridge hardcodes the (0,0) target — build
    the choke AT it),
  - "the bridge shape is a FEATURE: converge stories re-author with ZERO
    bridge forks; N pinned 129; density via GEOMETRY",
  - "the vision loop pays for camera work: expect 2-3 reframe rounds".
- **Mitigation**: all five survive in session-dated HANDOFF/USABILITY
  sections (HANDOFF.md:104-110, :136-141, :188-191; docs/
  USABILITY_TF1_last_ferry.md F-TF6) — so no law is lost from the REPO, only
  from the distilled SKILL surface that future kit sessions actually read.
- **Fix**: re-add a 5-bullet "SESSION 15 LAWS (film lane, condensed)" block
  to SKILL.md (there is byte headroom: 27,747 / 30,000 cap), or fold the
  bullets into the existing "SESSION 14/15 LAWS" block.

### F2D-9 · P2 — SKILL.md points at a nonexistent `experiments/physics_facts/`
- **Where**: `.agents/SKILL.md:211` — "Five measured laws (all verified via
  probes in `experiments/physics_facts/`)".
- **Reality**: no `experiments/` directory exists anywhere in the tree
  (checked). The five physics laws themselves are stated inline right below,
  so only the provenance pointer 404s.
- **Fix**: drop the parenthetical or re-point to the probe scripts that
  exist (e.g. `scripts/physics_place.py` probes / tests/test_t5_physics.py).

### F2D-10 · P2 — HANDOFF "verify BOTH PATs" bootstrap depends on helper scripts that are now half-broken and .env does not exist (fresh-clone ops path)
- **Where**: `HANDOFF.md:16-17` ("Verify BOTH PATs at session start (2-line
  curl check)") + the helpers `scripts/_sess16_gh_check.sh` (works, but with
  a dead-token placeholder → will report 401 forever until a fresh PAT is
  pasted in) and `_sess16_git_setup.sh` (re-writes origin from the REDACTED
  placeholder — actively breaks the GitHub remote; see F2D-2).
- **Fresh-clone runnability WITHOUT the redacted values**: otherwise GOOD —
  `install.sh` + suites + all kit tools are token-free (verified), reads are
  anonymous, and HANDOFF.md:41-44 documents clone→install→suites correctly.
- **Fix**: make both check helpers read the token from the environment
  (`GH_PAT="${GH_PAT:?export GH_PAT first}"`), and add `.env.example`.

### F2D-11 · P2 — PLAN.md "Queue (next)" still lists shipped work as open
- **Where**: `PLAN.md:266` — "3. t10 export suite. 4. VK-9 re-vendor (QA
  ask)." — item 3 shipped in session-16 (`tests/test_t10_export.py`, 19
  checks, verified); item 6 in the same list is marked CLOSED inline, items
  3/4 are not. (Item 4's VK-9 is the validate_scene twin re-vendor; the
  Wave A list closed F-TF5's wheel but never states VK-9's disposition —
  either close it with evidence or keep it, but say which.)
- **Fix**: annotate items 3 (CLOSED — t10 shipped, session-16) and 4
  (state the actual disposition).

### F2D-12 · P2 — Stale "which remote is authoritative" text survives in HANDOFF's session-8-era "Standing gotchas"
- **Where**: `HANDOFF.md:402-403` — "Current GitLab PAT is invalid (401) —
  mirror behind, **GitHub is authoritative**." This is now inverted twice
  over (session-16: GitLab primary; post-event: GitHub canonical again —
  F2D-3). Historical section, but it is one of the few places that states a
  *current-tense* remote truth, so a grep-based reader gets burned.
- **Fix**: append "(stale — see the session-16 close state + THE
  PUSH-PROTECTION EVENT for the current remote state)".

### F2D-13 · P3 — AGENTS.md exporter line-ref drifted: "exporter:1117"
- **Where**: `AGENTS.md:212-213` — "the CAM_ contract lives on the CAMERA
  OBJECT name (exporter:1117 …)".
- **Reality**: the enforcement raise is at `export_previz_package.py:1121-1124`
  (`if not cam.startswith("CAM_")` → SystemExit "expected a CAM_* object").
  `docs/USABILITY_S16_session16.md:88-89` records that the docstring edit
  shifted exporter line-refs by −5 and that the refs were "corrected" — but
  only inside the exporter/preflight surfaces; AGENTS.md kept the stale
  number. Mechanism description is otherwise exactly right.
- **Fix**: change to `exporter:1122`.

### F2D-14 · P3 — TD1 ledger's "Kit improvement filings (owner-repo candidates, not landed here)" list is stale for items 1 and 4
- **Where**: `docs/USABILITY_TD1_vision_film.md:106-114` — item 1 "F-TD5
  render_hidden_objects view_layer.update()" (landed upstream e4450a3 AND
  ported here — `blender_kit/__init__.py:932` verified) and item 4
  "make_material: pin Emission Color to base rgb (F-TD6)" (landed —
  `blender_kit/__init__.py:516,549` + F-TD11 kwargs). Closed-in-code,
  open-on-paper in that list (the ledger's own F-TD5 section at :131 says
  CLOSED, so the list contradicts the same file).
- **Fix**: mark items 1/4 CLOSED with pointers; keeps the ledger's
  open-set exactly {F-TD1, F-TD2, F-TD3, F-TD4?} (see recount below).

### F2D-15 · P3 — SKILL.md "Common meta-agent mistakes" numbering has holes
- **Where**: `.agents/SKILL.md:168-188` — items run 1-10, then 12, then
  15-22 (11/13/14 missing) — a compaction artifact.
- **Fix**: renumber.

### F2D-16 · P3 — Four different "work outside the watchdog dir" paths across docs
- **Where**: `.agents/SKILL.md:247` ("/home/z/blender-kit/"),
  `.agents/SKILL.md:172` ("/home/z/work/blender-vision-kit/"),
  `AGENTS.md:648` (gotcha 57, "/home/z/work/"), `HANDOFF.md:379`
  ("/home/z/vision-work clone").
- **Fix**: pick one canonical clone path and use it everywhere.

### F2D-17 · P3 — `scripts/_s16_nested_force.py` is a spent one-shot migration artifact whose own header lies if re-read
- **Where**: `scripts/_s16_nested_force.py:14-33` — EDITS lists v3/v2/v4/v7
  but the script applies only `EDITS[:2]`; the v4 entry is a no-op comment
  and the v7 entry has no replacement text. All four suites verified to
  ALREADY carry `BLRUN_FORCE=1` (grepped), so the script is dead weight that
  misdescribes its own state; it also sits in `scripts/` which is kit-scope
  territory (it does not trip test_kit_scope's `^scripts/(probe_)` ban).
- **Fix**: delete it, or move to smoke/ with a "spent, keep for provenance"
  header.

### F2D-18 · P3 — HANDOFF has TWO sections titled "Session-13 close state (NEWEST — read this first)" with different content
- **Where**: `HANDOFF.md:216` (D18/R9 asset-partition content) and
  `HANDOFF.md:533` (tdawn_2 content). Both merge parents already carried the
  duplication (p1 lines 168/485; p2 181/498) — so NOT merge damage, but one
  of the two is mislabeled (they cannot both be "the" session-13 close
  state).
- **Fix**: retitle one (e.g. "Session-13 close state — part 1: the D18/R9
  asset lane" / "part 2: the tdawn_2 iteration") or fold into one section.

---

## Doc-debt ledger recount (scope item 3) — clean numbers

| Filing | Claimed where | Reality at tip | Verdict |
|---|---|---|---|
| F-TD1 (cross-kit wheel install) | HANDOFF:79, PLAN:341 "remainder F-TD1/2/3"; TD1 ledger :37-43 | Fix owner is sibling crowd-kit's `setup_native.sh` (`--blender-python`); nothing landed here closes it (install.sh's BLENDER_PY override mitigates the THIS-kit side only) | **OPEN (correctly reported)** |
| F-TD2 (validator structural noise) | same; PLAN:374-375 lists it as next-session item | No structural/roof vocabulary in `validate_scene.py` (grepped) | **OPEN (correctly reported)** |
| F-TD3 (marker-camera hijack) | HANDOFF:47-49 "design first"; TD1 :52-60 | No marker handling in `look.py` / `viewport_capture.py` (grepped); look.py:88 only notes the probe path can't fire it | **OPEN (correctly reported)** |
| make_material default-arg (= F-TD6) | HANDOFF:206-208 + PLAN:341-342 "CLOSED" vs HANDOFF:78-82 + PLAN:397 still listing it | `blender_kit/__init__.py:516` signature + `:549` pin + `emission_color/emission_strength` kwargs (F-TD11) all present | **CLOSED everywhere in reality; still listed open in HANDOFF:78-82 and PLAN:397 (F2D-4/F2D-5) and in TD1's ask list (F2D-14)** |
| F-TF6 (kit-mode hero-lane pushout) | HANDOFF:80-82, TF1 ledger :73 "OPEN, kit candidate" | Nothing in kit-mode implements a hero-lane pushout | **OPEN (correctly reported)** |
| F-TF5 (wheel version seam) | TF1 ledger :62 "CLOSED — session-16 governed re-vendor" | `vendor/.../blender_crowd_native-1.5.5-…whl` + provenance README in-tree | **CLOSED everywhere ✓** |
| F-TD9 (install.sh Pillow probe) | HANDOFF:36-40 + PLAN:358 + S16 ledger: CLOSED vs HANDOFF:78 + PLAN:338/397: open | install.sh:141-180 authoritative probe + :88-93 QA-R69 heal | **CLOSED in reality; stale-open in the film-lane blocks (F2D-4/F2D-5)** |

Clean recount: **open = F-TD1, F-TD2, F-TD3, F-TF6 (+F-TG1's arrival-semantics
rider). Closed = F-TF5, F-TD9, make_material/F-TD6, F-TD5, F-TD10/11/12,
F18, F19, F20.** No filing is closed-in-code-but-open-on-paper except the
cosmetic TD1 ask-list entries (F2D-14); the film-lane blocks are
open-on-paper-while-closed-in-code (F2D-4/F2D-5).

## Receipts freshness (scope item 4)

- Battery: all **26** suite files named in `docs/battery_s16_results.md`
  exist at tip, names matching. Two extra test files exist but are outside
  the battery (`tests/x1_detection_matrix.py`, `tests/scene_cli_demo.py`,
  plus `tests/usd_smoke/`) — no suite was renamed/removed since; nothing in
  the receipt 404s. The contradiction is only F2D-6 (durable copy = pre-fix
  run; HANDOFF's 26/26 receipt was ephemeral).
- HANDOFF references **no** `output/audit_s16` paths (grepped — zero hits);
  `output/audit_s16/` does not exist on disk and nothing needs it. The only
  output/ reference in docs is the battery RESULTS path (F2D-6).

## Merge damage (scope item 1) — summary

- Conflict markers: NONE in any `*.md`, and none in scripts/tests/tools
  (only vendored Blender/Cython internals under `tools/blender-5.2.2…`).
- Dropped commit series: none — both lanes' full chains are reachable;
  parents are exactly the two lane tips.
- Resolved-to-the-correct-side: HANDOFF/PLAN filing checkboxes (F18/F19/F20/
  F-TF5/F-TD5) took the kit lane's accurate closure text; the film lane's
  stale lines were superseded (verified in the merge diff).
- Film-lane docs survived intact: `docs/DESIGN_green_light.md` (306 lines)
  and `docs/USABILITY_TG1_green_light.md` (121 lines) present at tip.
- Actual merge damage: F2D-7 (worklog duplication), F2D-8 (SKILL law-block
  loss), F2D-4/F2D-5 (stale film-lane claims unioned in beside fixes),
  F2D-3 (two "read first" session-16 sections with opposite recency
  claims — ordering marker collision, mild but real).

## SKILL.md hygiene (scope item 6)

- Size: **27,747 bytes** — under the 30,000 cap (headroom ≈ 2.2 KB).
- Claims verified against code at tip: look exit 3 + blrun propagation ✓;
  blrun per-display flock exit 90/LOCK-HELD/BLRUN_FORCE/BLENDER_DISPLAY ✓;
  four nested suites carry BLRUN_FORCE ✓; make_material(arg3=ROUGHNESS,
  emission via kwargs) ✓; shim helpers EEVEE_ENGINE_ID / normalize_engine_id /
  iter_fcurves / ensure_use_nodes / add_sky_world(NISHITA↔MULTIPLE_SCATTERING)
  / supports_headless_gpu all present in blender_kit ✓; test_v1_look 27
  checks ✓; resolution defaults (previz 480×270, look 640×480, motion
  480×360) ✓; KB entry list = exactly the 10 existing kb/ files ✓; blind
  machinery (ascii_vision/vlm_critique) absent ✓; crowd stub absent ✓;
  tgreen_/tferry_/scene_green_light module set all exists ✓. Contradicted
  claims: F2D-1 (repo names), F2D-8 (dropped laws), F2D-9
  (experiments/physics_facts), F2D-15 (numbering), F2D-16 (clone path).
