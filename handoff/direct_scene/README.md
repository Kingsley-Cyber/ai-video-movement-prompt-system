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
| 4 | `PLAN.md` | the approach, where each piece goes, all slices in order, and what carries over |
| 5 | `WORK_ORDER_01_scene_action.md` | the first pass, specified to the field and test name |
| 6 | `OWNER_ACTIONS.md` | what only the owner can do |
| — | `reference/` | source material to adapt: owner statements, the 16 passes, validator rules, the jail-fight fixture, the "before" probe |

To start an agent, paste the block in `START_HERE.md`.

## What this folder is not

- Not a second roadmap. Slices here are the remediation order for `REQ-077`; update that row,
  not this folder, when status changes.
- Not a compiler or a knowledge store. Files under `reference/` are material to adapt under the
  owners named in `PLAN.md`. Do not import them as a package or copy them into `lab/` wholesale.
- Not curated knowledge. Nothing here is reviewed research.
