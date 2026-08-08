# Upstream method decisions

These projects informed the CPCS repository-control workflow. They are design references, not
runtime dependencies.

## Superpowers

Source: `obra/superpowers` at commit `44c9b2d6e889982ac18c27d05a19fefe335194e1`, MIT.

Adopted mechanics:

- Define exact files, interfaces, tests, and verification before implementation.
- Execute one reviewable slice at a time.
- Trace root cause before repair.
- Require fresh verification before completion claims.

Rejected mechanics:

- A separate `docs/superpowers/plans/` plan authority.
- Mandatory commits inside each task. CPCS commits only with owner authorization.

## Beads

Source: `gastownhall/beads` at commit `1174876c80384f6c759dc5c350d15bc027c9c4f4`, MIT.

Adopted mechanics:

- Dependency-aware ready work.
- Stable work IDs and closed lifecycle events.
- Structured agent-readable output and an audit trail.

Rejected mechanics:

- Dolt, `.beads/`, Git hooks, and a second task database. `ARCHITECTURE.md` remains CPCS work-state
  authority and the implementation event ledger records execution evidence only.

## Aider repository map

Source: `Aider-AI/aider` at commit `5dc9490bb35f9729ef2c95d00a19ccd30c26339c`, Apache-2.0.

Adopted mechanics:

- Extract definitions and references to rank relevant code context.
- Treat repository maps as derived and refreshable.

The first CPCS slice uses Python AST imports, reverse test links, routed owners, requirement mentions,
and a Git WIP overlay. Tree-sitter symbol extraction and PageRank remain later performance or
precision improvements, not prerequisites for the control boundary.
