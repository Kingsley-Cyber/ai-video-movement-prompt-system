# Repository-control operating contract

Read `../../AGENTS.md`, `../AGENTS.md`, `../registry.yaml`, and `../../ARCHITECTURE.md` first.

`ARCHITECTURE.md` remains the sole implementation-state and requirement-gap authority.
`REPO_CONTINUITY_IMPLEMENTATION_PLAN.md` remains the target dependency-order owner. This subsystem
does not create another roadmap, product ontology, runtime workflow, or knowledge graph.

The repository-control plane owns five things:

1. A deterministic repository map derived from files, Python imports, tests, routed owners, and the
   architecture requirement table.
2. A dependency-aware view of implementation requirements and their current categorical status.
3. An append-only, hash-chained implementation-event log for admitted work, checkpoints,
   verification, failures, and completion evidence.
4. Read-only impact analysis that overlays current Git WIP without writing WIP state into the stable
   repository map.
5. A human-readable layer map generated from the same graph and root directory contract.

The stable machine map is `derived/repository_map.json`; its human projection is
`derived/REPOSITORY_LAYER_MAP.md`. Never hand edit either file. Rebuild both with:

```bash
python3 lab/repo_control/src/control.py rebuild
```

Every implementation slice must name one `REQ-*` owner, its files, verifier, and rollback boundary.
Use `impact` before editing and `check` before claiming the slice works. Logs record what an agent
did; they do not override Git, tests, architecture status, human approval, or production gates.

Upstream methods are design references only. CPCS does not install Beads, Dolt, Git hooks, Aider,
or Superpowers as repository runtime dependencies.
