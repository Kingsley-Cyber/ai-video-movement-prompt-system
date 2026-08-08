---
name: cpcs-repo-control
description: Control CPCS implementation and refactoring work through its live architecture requirements, deterministic repository map, dependency-ready queue, impact graph, append-only work log, and verification gates. Use for goal-mode execution, implementation planning, bug fixing, refactoring, repository reorganization, directory ownership changes, WIP recovery, impact analysis, completion checks, or selecting the next CPCS slice.
---

# CPCS Repository Control

Keep `ARCHITECTURE.md` as implementation-state authority and
`REPO_CONTINUITY_IMPLEMENTATION_PLAN.md` as target order. Do not create a parallel roadmap, task
file, issue database, or graph.

## Execute one slice

1. Read root `AGENTS.md`, `lab/repo_control/AGENTS.md`, and the routed owner contract.
2. Run `python3 lab/repo_control/src/control.py check`.
   Use `lab/repo_control/derived/REPOSITORY_LAYER_MAP.md` for a compact directory and owner guide.
3. Run `python3 lab/repo_control/src/control.py ready`; select one dependency-ready `REQ-*` row.
4. Run `python3 lab/repo_control/src/control.py impact <path>` for every proposed owner path.
5. Log `started` with one stable `work_id`, the requirement, scope, and expected verifier.
6. Implement the smallest vertical slice. Do not edit derived maps by hand.
7. Run the requirement verifier, owner tests, repository-control tests, and full repository gate.
8. Log `verification`, then `completed` only when fresh output proves the claim. Update the
   architecture row with exact entrypoint, wiring, outcome, and `verification:PASS` evidence.
9. Run `python3 lab/repo_control/src/control.py rebuild` and `check` after the final documentation
   update.

Use `blocked` for a named external blocker and `abandoned` when a slice is deliberately discarded.
Never log `completed` because code exists, a mock passes, an agent reports success, or a percentage
looks high.

## Refactor mode

Start from `impact`, not filename intuition. Inspect owners, reverse imports, tests, requirements,
and the Git WIP overlay. Preserve unrelated dirty changes. If ownership moves, update routing,
registry pointers, tests, and the generated map in the same slice. Keep the knowledge graph, Video
Observation Graph, and repository implementation graph separate.

## Failure mode

For a failing test, reproduce and trace the first bad boundary before editing. Record one
hypothesis per checkpoint. After three failed repair attempts, log `blocked` and re-evaluate the
architecture rather than layering a fourth patch.

Read [references/upstream-methods.md](references/upstream-methods.md) only when changing this skill
or its control-plane design.
