# Handoff: make CPCS direct a scene

**Repository:** `Kingsley-Cyber/ai-video-movement-prompt-system`. Work happens here and nowhere
else. Do not build in, copy to, or push to any other repository.

This folder is the owner's brief for an implementing agent. It holds the intent, the verified
context, the plan, and one fully specified work order for the first pass. It holds **no
implementation status**: status lives in `ARCHITECTURE.md` (row `REQ-077`), and the repository's
own laws in the root `AGENTS.md` win over anything written here.

## Read in this order

| # | File | What it gives you |
|---|---|---|
| 1 | `../../AGENTS.md` | the repository's laws, routing and gate (always first) |
| 2 | `INTENT.md` | what the owner wants, in his words and in plain rules; what counts as done; what is out of scope |
| 3 | `CONTEXT.md` | what the code does today, with file and line; what was built elsewhere; traps already found |
| 4 | `PLAN.md` | the consolidated REQ-077 build order, slices A–E, and resolved instruction conflicts; ARCHITECTURE owns status |
| 5 | `REGISTRY.md` | the fixed selection sets: principles, entry format, standing of every set, open flags |
| 6 | `INTEGRATION.md` | the owner's requirements at field level, each mapped to a slice of Codex's master plan |
| 7 | `PROMPT_SKELETON.md` | the owner's natural-language prompt layout: the target the build must be able to write |
| 8 | `WORK_ORDER_01_scene_action.md` | the first pass (completed in commit `a775f35`; kept for the record) |
| 9 | `OWNER_ACTIONS.md` | what only the owner can do |
| — | `reference/` | source material to adapt: owner statements, the 16 passes, validator rules, the jail-fight fixture, the "before" probe, the owner's kitchen-fight skeleton example, and the owner's pasted notes (registry draft, clock and formats, closed-loop camera, movement architecture, fixed set loop), each verbatim and unverified |

Owner clarification on 2026-10-03: the generated instruction to stop after work order 01 did
not reflect the intended scope. Continue the ask-to-prompt path end to end under the existing
owners and gates. Work order 01 remains a compatibility reference, not a stopping boundary.
Provider spend, renders, promotion and pushing still require explicit owner instruction.

Owner clarification: the NL baseline needs reasoning about its creative content, not just a new
layout. Accepted action, movement, staging and camera choices must reach the NL description as
they reach structured controls. NL, YAML, XML, JSON and requested hybrids remain live forms.
PLAN.md governs proposed records here and historical external specifications; source evidence
does not override current owner intent. External analyses are review snapshots, not task lists.

To start an agent, paste the block in `START_HERE.md`.

## What this folder is not

- Not a second roadmap. Slices here are the remediation order for `REQ-077`; update that row,
  not this folder, when status changes.
- Not a compiler or a knowledge store. Files under `reference/` are material to adapt under the
  owners named in `PLAN.md`. Do not import them as a package or copy them into `lab/` wholesale.
- Not curated knowledge. Nothing here is reviewed research.
