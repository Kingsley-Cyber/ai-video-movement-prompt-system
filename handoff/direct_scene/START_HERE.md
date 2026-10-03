# Start here

Paste this block into a coding agent opened on this repository.

```text
You are implementing one work order in the repository Kingsley-Cyber/ai-video-movement-prompt-system
(this checkout). Work only in this repository. Never create, edit or push another repository.

1. Read, in order: AGENTS.md (root), handoff/direct_scene/README.md, INTENT.md, CONTEXT.md,
   PLAN.md, then WORK_ORDER_01_scene_action.md in full. Then read the owner contracts the work
   order names: lab/repo_control/AGENTS.md, skills/cpcs-repo-control/SKILL.md,
   lab/second_brain/AGENTS.md, lab/compiler/AGENTS.md, lab/application/AGENTS.md.
2. Confirm the starting state before editing: branch `direct-scene`, clean worktree,
   `python3 lab/repo_control/src/control.py check` green. If any of these is false, stop and say so.
3. Execute WORK_ORDER_01_scene_action.md only. Write each test before the code it tests. Do not
   edit any existing test. Do not start the next slice.
4. Follow the repository's slice procedure (skills/cpcs-repo-control/SKILL.md): log `started`,
   implement, run owner tests, run `python3 lab/scripts/validate_repo.py` (about 9 minutes, must
   exit zero), log `verification` and `completed`, rebuild and check the repository map, update
   the REQ-077 row in ARCHITECTURE.md with entrypoint, wiring, outcome and verification, add one
   CHANGELOG.md line, commit locally on `direct-scene` with an imperative subject and the
   agent Co-Authored-By line.
5. Do not push. Do not open a pull request. Do not promote curated knowledge. Do not call a
   video or analysis provider. The owner says "push" when he wants it on GitHub.
6. If an instruction is missing or two conflict, take the most conservative choice, record it in
   your final report as a guess, and continue. If a rule in the root AGENTS.md conflicts with this
   folder, AGENTS.md wins. After three failed repair attempts on one failure, stop and report the
   exact error.

Final report, under 400 words: files created or changed; test counts; the gate's last line; the
jail-fight result through the public CLI (score id, counts of entities, beats, actions,
interactions, the kept duration, the provider-fit line); every guess; the commit hash; what is
proven by tests and what has no render behind it.
```

After the agent stops, start a new session with the same block and the next work order when one
exists. Work orders for later slices are written only after the previous slice is committed.
