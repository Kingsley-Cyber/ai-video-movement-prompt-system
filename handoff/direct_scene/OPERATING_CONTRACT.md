# CPCS operating contract (standing; read at the start of every session)

This is the standing control layer for work on `/Users/king/ai-video-movement-prompt-system`. Round
briefs carry only what changes per round. This file carries what never changes between rounds.

**Precedence:**
1. Root `AGENTS.md` laws
2. this contract
3. the current round brief
4. plan documents in `handoff/direct_scene/`

A lower level never overrides a higher one.

## 1. Roles

| Role | Who | Owns |
|---|---|---|
| Owner | King | Truth and taste: which members are admitted, render verdicts, champions, model/route, spend, push |
| Builder | Codex | Code, tests, governance records, local commits, round reports |
| Reviewer | Claude | Specs, round briefs, review of every round's commits before the next round |
| Researcher | external research agent | Candidate inventories only; never admitted until the owner approves the members |

## 2. Standing authority

**Always allowed:**
- code, new tests, schema extensions and docs inside the repository;
- local commits under the gate;
- reading research and evidence folders.

**Never without the owner's word in the current brief:**
- push, PR or network;
- renders, provider or analysis calls;
- spend;
- curated promotion;
- changing champion files;
- editing tests that existed before the round;
- pose extraction on real renders.

**Never:**
- printing or storing API keys;
- touching another repository;
- copying video into git;
- inventing values, tolerances, scores or sources.

## 3. Decide and log, or stop

**Default: decide by rule and keep going.** Every decision goes into the report's "Decisions
made" list, with the rule used. A round runs all its parts without pausing between them.

| Situation | Action |
|---|---|
| A rule in the brief or section 5 covers it | Apply it; log it |
| No rule covers it, it is reversible, and it stays inside the brief's scope | Choose the smallest option that keeps every acceptance item true; log it as `judgment` |
| A test you wrote this round is wrong | Correct it from the definition, never from the code's output |
| An existing test was already failing | Record the command and output; continue unless the gate is red because of it |
| Missing optional evidence | Record it as unknown; continue |

**Stop only when:**
1. a safety boundary in section 2 would be crossed;
2. an owner-only decision (section 1) has no rule;
3. the brief contradicts an `AGENTS.md` law;
4. the gate stays red after the existing repair fuse;
5. required evidence is missing and no part of the remaining work can proceed without it.

**On a stop:**
- commit nothing broken;
- finish every independent part that can still be finished;
- then report.

## 4. Round lifecycle

1. Read this contract.
2. Read the round brief.
3. Run the bootstrap checks.
4. Build all parts, with the gate and a local commit per part.
5. Send one final report.
6. Claude reviews.
7. The owner approves.
8. The next brief arrives.

## 5. Standing decisions (accumulates; newest last)

| ID | Decision | Since |
|---|---|---|
| SD-1 | Natural language is the baseline carrier; structure improves it; JSON/YAML/XML/hybrid stay supported options | R0 |
| SD-2 | Relative anchors and source-status evidence sets are kept as they are | R0 |
| SD-3 | The builder never reads champions or `/Applications`; champions are test oracles only | R1 |
| SD-4 | Byte accounting is measured after wrapping. `typed_bound` = bound values; `authored_clause` = authored text as printed; `layout` = everything else, including consumed whitespace and builder punctuation | R1 |
| SD-5 | "Existing tests" = tests tracked at the round's base commit | R1 |
| SD-6 | A manual render's prompt binding is `owner_attributed`; submitted text, seed, model, route, settings and requested frame rate stay unknown unless proven; unknown never equals unknown | R1 |
| SD-7 | Owner statements are verbatim and marked `owner`; Claude's observations are marked `Claude`; paraphrase is labelled | R1 |
| SD-8 | Flow is selected independently; basic effort actions fix Weight/Time/Space only | R2 |
| SD-9 | Kinetic-chain adjacency, per side: foot–ankle–knee–hip–pelvis–spine–chest–shoulder–elbow–wrist–hand, plus head–neck–spine. The sides join at the pelvis and the chest | R2 |
| SD-10 | A6 phrase → repository phase: preparation → preparation; initiation + stroke → execution; end of stroke → contact-or-apex; follow-through → follow-through; recuperation → recovery | R2 |
| SD-11 | Comparator tolerances are explicit inputs; unset means `uncalibrated` (report-only) | R2 |
| SD-12 | Every admitted member enters with `model_support: untested`; only recorded renders change it | R2 |
| SD-13 | Layer order for closing loops: Laban/Bartenieff → camera → FACS → physics/contact → others | R2 |
| SD-14 | Brain-health and domain-coverage acceptance is relative to the base snapshot. Record pre-existing attention-required findings (historical source closure, unconfigured Neo4j, graph reachability, seed-only coverage). Promotion passes if it introduces no new findings and does not worsen existing ones. Do not fix unrelated pre-existing findings this round. | R2 owner correction |

| SD-15 | Kinematic frame convention: metres, y up, support surface y = 0, +x screen-right for a camera facing +z, cameras as position + `look_at` (TIMING_AND_KINEMATICS.md) | owner 2026-10-04 |
| SD-16 | Closed lists approved as project conventions: support parts and manner, contact modes, force events (TIMING_AND_KINEMATICS.md "Owner-approved conventions") | owner 2026-10-04 |
| SD-17 | Timing is a carrier choice and is tracked: the score derives a canonical timeline from complete beat lengths; every scene build records the printed timing form beside the plan with no adherence claim; observed timing and calibration follow only from scored renders | owner 2026-10-04 |
| SD-18 | Kinematics is always on: every complete directing session must carry a validated kinematic plan in staging; there is no off switch. The owner permitted adding plans to the protected tests that complete staging | owner 2026-10-04 |
| SD-19 | Closed Laban/Bartenieff movement sets are always on in complete directing: no `movement_sets` option; Effort, Shape and connectivity slots take admitted codes. The owner permitted the matching protected-test updates | owner 2026-10-04 |
| SD-20 | Test cadence: before every commit run the affected owner tests and repository-control tests; run the full gate (stdin closed) before every push. Pushes never carry an ungated commit. The gate is made fast without checking less (owner 'yes do 1 and 2'): owner suites run together, suites that need the exclusive authority lock run alone, a suite that fails beside others is re-run alone and that result counts, and the scale benchmark is reused while everything it reads is byte-identical to its last passing run in the checkout (`CPCS_GATE_FULL=1` forces it) | owner 2026-10-04 |

Add a row only when the owner or a reviewed brief decides something durable.

## 6. Research inbox protocol

- **Location:** research arrives in `/Users/king/.zcode/workspace/default/deep_research/`.
- **Readiness:** a batch is ready only when `MANIFEST.json` in that folder lists it with status
  `READY` and its SHA-256, and the file on disk matches that hash. Anything else is in progress:
  ignore it.
- **Reading:**
  - Record the hash at read time and bind any intake to it.
  - Markdown wins over JSONL when they disagree.
  - Ignore research `model_support` values.
- **Status:** research members are candidates. Admission needs the owner's member list in a brief.

## 7. Report format (every round)

1. **First line:** `ROUND DONE` or `ROUND STOPPED: <condition and reason>`.
2. **Bootstrap results.**
3. **Commits:** hash, one line each, and the gate's last line for each.
4. **Per-part acceptance:** each item with the test that proves it.
5. **Decisions made:** each with the rule or `judgment`.
6. **Unknowns recorded.**
7. **Proof vs efficacy:** what is software proof; no render efficacy is claimed unless renders were
   authorized and recorded.
8. **Owner items:** only genuine owner decisions.
