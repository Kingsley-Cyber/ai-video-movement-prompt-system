# WP-1 — Schemas + Contracts (no engine logic)

Depends on: nothing (can run first, in parallel with WP-6 schema).

## Deliverables

Create in `lab/application/`:

1. `CPCS_PRINCIPLE_PACK_SCHEMA_v0.1.json`
   - principle (structured template text)
   - mechanism (structured template text)
   - failure_risk (failure_family_ids + risk template)
   - evidence_ids (array; D4: IDs only)
   - source_records (array of {atomic_record_id, universal_type, epistemic_status})
   - intent_application (structured: domain tags, creative goal tags)
   - pack_id + pack_hash + lineage

2. `CPCS_REPRESENTATION_DECISION_SCHEMA_v0.1.json`
   - decision enum: CONTROL | VERIFICATION | PLANNING | NON_EXECUTABLE | COMPOSITE
   - rationale, authority (authority order), target_family (registry path_id or null)
   - forbidden_coercions (from registry)
   - verification_counterpart (or null)
   - decision_hash

3. `CPCS_KNOWLEDGE_APPLICATION_CONTRACT_v0.1.json`
   - flow: RetrievalEvidencePacket -> KnowledgeApplicationSet -> Typed Controls
   - the three-question split (retrieval / reasoning / bridge)
   - affordance mapping rule: TC-2 dispositions + DR-1 affordance ledgers are
     the inputs that decide CONTROL vs VERIFICATION vs PLANNING vs NON_EXECUTABLE
   - D4 + authority order restated
   - 97-non-executable-objects policy: they are reasoning material, never
     controls; they may emit PLANNING or NON_EXECUTABLE decisions only

## Acceptance tests (file `lab/application/tests/test_ka1_schemas.py`)

- all three JSON artifacts parse
- decision enum exhaustive; authority values subset of frozen order
- a validation script `python3 -m lab.application.ka1_schemas_validate`
  validates sample PrinciplePack/RepresentationDecision instances against
  jsonschema Draft202012 validators embedded in the schema files

## Forbidden

- No changes to `cpcs_typed.py` registry semantics (WP-6 owns that file; if you
  need a registry field, add it to a NEW optional key, never rename).
- No service.py/MCP changes (WP-8 owns registration).

## Done when

Three artifacts exist, validate, and the schema test passes.
