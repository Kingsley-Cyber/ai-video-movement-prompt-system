# Changelog

## 1.0.0 — 2026-07-19

Initial standalone CPCS-MX research package.

### Research

- Added the full monograph, **CPCS-MX: A Hierarchical Motion Grammar for Exact, Expressive, and Superhuman Character Performance**.
- Formalized multiple meanings of exactness: source-clock, screen-space, rig-space, world-space, dynamic, and perceptual.
- Integrated root motion, joint tracks, phases, contacts, biomechanics, IK, retargeting, Laban, FACS-like face control, gaze, breath, mannerisms, and secondary motion.
- Defined natural movement, realistic UGC, staged action, anime/sakuga, and virtual-superhuman style domains.
- Reframed superhuman motion as typed, phase-specific transformation with protected invariants rather than a single intensity scalar.
- Separated anatomical constraints, rig-safe constraints, virtual motion, deformation, camera, editing, and VFX.
- Added agent architecture, text-to-structured compilation, capability negotiation, and closed-loop verification.

### Data contracts

- Added canonical CPCS-MX JSON Schema.
- Added authoring YAML/JSON Schema.
- Added observation JSONL and RAG-record schemas.
- Added evidence, authority, provenance, safety, and verification contracts.

### Agent and RAG assets

- Added semantic RAG JSONL with research chunks, schema definitions, examples, profiles, prompts, documentation, and 80 source records.
- Added authoring, verification, and style-transfer prompts.
- Added agent ingestion guidance and practical workflow recipes.

### Examples and scripts

- Added natural walk, realistic UGC, staged near-contact, anime-superhuman, and cross-style examples.
- Added a synthetic dense joint-track asset with SHA-256 validation.
- Added deterministic YAML compilation, JSONL streaming validation, observation merging, RAG building, and full-package validation scripts.
