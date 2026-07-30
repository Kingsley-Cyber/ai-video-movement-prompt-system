# Polymath MCP operational-knowledge distillation prompt

Use this prompt with the implementation agent after the proposal schema, writer, and validator pass.

## Mission

Use the connected **Polymath MCP** as an external research library to propose compact, operational
knowledge for the CPCS second brain. Do not copy the corpus into the repository. Distill only
knowledge that can change a reasoning, compilation, experiment, validation, diagnosis, or explanation
decision.

## Tool discovery first

Before retrieval:

1. Enumerate the MCP tools and resources actually connected in this runtime.
2. Record their exact names, arguments, pagination, returned source IDs, locator fields, and read/write
   permissions in `work/second_brain/mcp_inventory.json`.
3. Do not invent tool names from this document.
4. If unavailable, write the exact blocker and continue every task that does not require MCP access.

## Priority domains

Process in small batches:

1. cinematography, lighting, lensing, framing, composition, and camera movement;
2. acting, gesture, gaze, facial behavior, FACS, affect, BML, Laban/BESS, and movement phrasing;
3. animation principles, choreography, action phases, biomechanics, kinematics, contact, balance,
   dynamics, secondary motion, and stylization;
4. editing, retiming, audio, speech alignment, sound design, captions, and audiovisual synchronization;
5. UGC authenticity, communication structure, product demonstration, proof, CTA, and experiment design;
6. motion capture, skeleton topology, retargeting, OpenUSD, glTF, pose/depth/mask/flow control assets;
7. provider/model capability documentation, supported inputs, limitations, degradation paths, and
   version-specific behavior;
8. validation metrics, round-trip extraction, semantic signatures, failure diagnosis, and evidence
   methodology.

## Per-batch procedure

For each domain:

1. Query Polymath for source passages addressing executable controls, relationships, constraints,
   measurable parameters, mappings, failure modes, or validation methods.
2. Retrieve the smallest evidence bundle needed to support each candidate. Preserve source ID,
   work/title, section/page/locator, corpus, and a content hash when available.
3. Search `lab/concepts.jsonl` and the live graph for semantic and literal duplicates.
4. Prefer extending an existing `c_*` card or proposing an authored edge/mapping over creating a new
   synonym.
5. Propose only atomic operational concepts. A concept should have one primary reasoning function.
6. Use a free-string `layer`, but reuse an existing layer when it is semantically correct.
7. Populate `encodable_as` only for real representations: `prose`, `numeric`, `ordinal_xml`,
   `au_enum`, `laban_effort`, or `media_asset`.
8. Add `params` only when a source-supported numeric/enum control exists. Never invent ranges.
9. Mark source-derived but untested generation behavior `unexplored` or `partial`; literature truth is
   not provider conformance.
10. Write proposal JSONL only. Do not write curated records.

## Proposal quality test

Reject or leave in the external RAG when the knowledge is:

- merely descriptive background;
- a raw entity or sentence with no CPCS operation;
- unsupported by a stable source;
- a duplicate label with different wording;
- too broad to test or map;
- provider marketing not verified against a version;
- a claimed causal effect without an isolated experiment.

Promote candidates that can answer at least one:

- What control should be selected?
- What concept pairs or conflicts with another?
- What representation carries it?
- What parameters or units constrain it?
- What provider path can execute it?
- What must remain invariant?
- What experiment would test it?
- What metric verifies it?
- What failure does it diagnose?

## Required proposal output

Emit one JSON object per line conforming to
`lab/second_brain/schemas/proposal.schema.json`.

Every proposal must include:

- unique `proposal_id`;
- `proposal_type`;
- complete candidate record;
- non-empty `source_evidence`;
- dedup candidates and similarity scores when available;
- actual Polymath source identifiers and locators;
- creator and timestamp.

At the end of each batch, produce a report with counts:

```text
retrieved sources
candidate concepts
candidate edges
candidate mappings/rules
duplicates merged
proposals written
proposals rejected
unsupported numeric claims
```

Then validate proposals and inspect their graph neighborhood before requesting promotion.
