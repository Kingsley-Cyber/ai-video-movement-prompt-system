# FORMAT ↔ CONTROL MAP — which format carries which control, and why

The papers assign each serialization format to the control types it handles best (CPCS §19.3/19.5–19.8,
RDC §6, MX README format table). This is the clean, sorted mapping. It is an **authoring/architecture**
rule — who writes what, in what carrier — distinct from the paste-format question (see Nuances).

## The three superpowers

| Format | Superpower | Owns |
|---|---|---|
| **YAML** | Human readability · `extends:` inheritance · imports · comments | creative intent, style, transfer policy |
| **JSON** | Machine precision · arrays · schema validation · hashing | exact numbers, canonical resolved score |
| **XML** | Ordered mixed content · namespaces · explicit triggers · XSLT | script order, event/trigger tracks |

Plus the two carriers the trio rides on:

| Carrier | Role |
|---|---|
| **JSONL** | append-only evidence stream: observations, corrections, conflicts, validation events (RDC §6.1) |
| **Media/arrays** | dense pose/masks/depth/flow/camera stay as media — never serialized into prose (c_dense_assets_media) |

## Control-by-control assignment

| Control layer | Format | Why |
|---|---|---|
| Narrative (beats, objectives, subtext) | **YAML + XML** | YAML for structure; XML when script ORDER must be preserved |
| Marketing (hook deadline, product visibility) | **YAML** | human-reviewable constraints |
| Safety/Rights (consent, identity locks) | **YAML** | easy to review and approve |
| Affect (VAD curves, experienced vs displayed) | **YAML** | human-readable curve knots |
| FACS (AU events, onset/apex/offset, intensity) | **XML + JSON** | XML for event triggers; JSON for exact splines |
| Gaze/Breath/Blink | **XML** | trigger-based, ordered, event-driven |
| Body action (action atoms, posture labels) | **YAML + JSON** | YAML labels; JSON joint positions |
| Laban (Effort/Shape/Body/Space) | **YAML** (words) / **JSON** (float vectors) | qualitative authoring vs numeric canonical (v005 `lab_control`) |
| Kinematics (root, joints, contacts) | **JSON** | machine-generated exact arrays — solver output |
| Camera/Director (6DoF paths, lens, edit) | **JSON + XML** | JSON exact paths; XML event-triggered moves |
| VFX triggers (flash, shockwave, speed lines) | **XML** | namespaced (`vfx:`), time-anchored triggers |
| Audio cues (SFX, breath, music hits) | **XML** | ordered, time-aligned triggers (`audio:`) |
| Verification metrics + provenance | **JSON** | machine-checkable targets/tolerances |
| High-level hard constraints ("no slow-mo") | **YAML** | director-authored, reviewable |

## The production flow (who writes what, in order)

```
DIRECTOR (human)      → YAML   intent, style extends:, beats, Laban, constraints
SOLVER (machine)      → JSON   exact joints, contact times/distances, camera 6DoF
DIRECTOR (2nd pass)   → XML    ordered script envelope + audio/VFX triggers + <score href="…json" sha256>
COMPILER              → merges YAML+JSON+XML → unified canonical JSON (inheritance materialized,
                        order preserved, kinematics inlined, provenance tracked)
TARGET MODEL          → compiled prompt + first/last frames + optional control assets
```

XML references the JSON by hash (`<cpcs:score href="asset://….json" sha256="…"/>`) — it does not
duplicate the numbers. One authority per quantity (MX §3.3).

## Why three formats instead of one

| Problem | Solved by |
|---|---|
| YAML alone can't carry ordered mixed content (prose + tags) | XML |
| JSON alone is hostile to human authoring (no comments, no inheritance) | YAML |
| XML alone is far too verbose for dense numerics | JSON |
| YAML+JSON lose department-namespaced trigger tracks | XML namespaces |
| JSON+XML lose style inheritance (`extends:`, imports) | YAML |

## Nuances (honesty box)

1. **Order:** JSON *arrays* and YAML *sequences* DO preserve order — the unordered risk is
   objects/mappings. XML's real edge is ordered **mixed content** (prose interleaved with tags),
   department **namespaces**, and XSLT — not order alone. Use arrays for ordered data in JSON; use
   XML when narrative prose and triggers must interleave.
2. **This map ≠ the paste question.** This governs *authoring architecture* (who writes what).
   What you paste into a capped input box is separate: format doesn't raise realism (p006), numeric
   structure IS control for motion (p008), and format-swap yields output variance (p009). The compact
   YAML-in-XML / YAML+JSON house formats are *paste packagings* of this architecture, not replacements.
3. **Layer alignment:** this table uses the CPCS control-layer names; they nest inside the 14-layer
   MX skeleton (intent/action/phase… map to L1–L14). Same content, two views.

Cards: `c_format_control_map`, `c_house_formats`, `c_two_document_architecture`, `c_dense_assets_media`.
