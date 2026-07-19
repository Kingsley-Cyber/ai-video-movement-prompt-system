# CPCS-MX Package Structure

```text
CPCS_MX_Hierarchical_Motion_Grammar_Research_Package_v1.0/
├── README.md
├── NOTICE.md
├── CHANGELOG.md
├── CITATION.cff
├── SHA256SUMS.txt
├── paper/
│   └── CPCS_MX_Hierarchical_Motion_Grammar_Research_Paper.md
├── rag/
│   └── CPCS_MX_RAG_Corpus.jsonl
├── schemas/
│   ├── CPCS_MX_Schema.json
│   ├── CPCS_MX_Authoring_Schema.json
│   ├── CPCS_MX_Observation_Record_Schema.json
│   └── CPCS_MX_RAG_Record_Schema.json
├── scripts/
│   ├── build_cpcs_mx_rag.py
│   ├── compile_authoring_yaml.py
│   ├── merge_cpcs_mx_observations.py
│   ├── validate_jsonl_stream.py
│   └── validate_cpcs_mx_package.py
├── profiles/
│   ├── movement/
│   │   ├── natural_human_v3.yaml
│   │   └── staged_action_base_v2.yaml
│   ├── capture/
│   │   └── authentic_ugc_v2.yaml
│   ├── style/
│   │   └── anime_sakuga_action_v3.yaml
│   ├── screen_action/
│   │   └── staged_near_contact_v2.yaml
│   ├── camera/
│   │   ├── impact_readability_v1.yaml
│   │   └── observational_medium_wide_v1.yaml
│   └── performance/
│       └── confident_direct_v1.yaml
├── examples/
│   ├── canonical_cpcs_mx_score.json
│   ├── natural_walk.yaml
│   ├── realistic_ugc_gesture.yaml
│   ├── staged_combat_exchange.yaml
│   ├── anime_superhuman_action.yaml
│   ├── cross_style_transform.json
│   ├── compiled/
│   │   ├── natural_walk.compiled.json
│   │   ├── natural_walk.compiled.report.json
│   │   ├── realistic_ugc_gesture.compiled.json
│   │   ├── realistic_ugc_gesture.compiled.report.json
│   │   ├── staged_combat_exchange.compiled.json
│   │   ├── staged_combat_exchange.compiled.report.json
│   │   ├── anime_superhuman_action.compiled.json
│   │   └── anime_superhuman_action.compiled.report.json
│   ├── observations/
│   │   ├── motion_observations.jsonl
│   │   ├── merged_active.jsonl
│   │   ├── normalized_all.jsonl
│   │   └── conflicts.json
│   └── tracks/
│       └── actor_a_joints_rot6d.npz
├── prompts/
│   ├── TEXT_TO_CPCS_MX_AGENT_PROMPT.md
│   ├── CPCS_MX_VERIFIER_AGENT_PROMPT.md
│   ├── CPCS_MX_STYLE_TRANSFER_AGENT_PROMPT.md
│   └── cpcs_mx_agent_request.xml
├── references/
│   ├── CPCS_MX_Reference_Index.md
│   ├── CPCS_MX_Reference_Index.json
│   ├── CPCS_MX_Reference_Index.csv
│   ├── CPCS_MX_Source_Annotations.jsonl
│   └── CPCS_MX_Source_URLs.tsv
├── docs/
│   ├── AGENT_INGESTION_GUIDE.md
│   ├── AGENT_WORKFLOW_RECIPES.md
│   ├── SCHEMA_FIELD_GUIDE.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   └── PACKAGE_STRUCTURE.md
└── manifests/
    └── CPCS_MX_Package_Manifest.json
```

## Paper

The monograph is the conceptual and research foundation. It uses stable `[S###]` source IDs and explicit `RAG_CHUNK` markers.

## RAG

The JSONL corpus is the preferred ingestion artifact for agents. It is rebuilt from the paper, schemas, examples, profiles, prompts, documentation, root package documents, and source index by the build script.

## Schemas

The canonical score, authoring input, observation stream, and RAG record have separate contracts.

## Profiles

Profiles provide versioned defaults. They are examples and project conventions, not universal movement standards.

## Examples

Examples are fictional and safety-scoped. The staged-action example uses near-contact. The dense NumPy track is synthetic and exists for parser and hash testing, not as a biomechanical reference.

## Scripts

Scripts avoid network access and use safe parsing. The reference compiler intentionally reports unresolved semantic work rather than claiming a complete motion-generation system. JSONL tools process records incrementally and preserve conflicts rather than averaging incompatible claims.

## References

The package carries 80 source records in several index formats. Source annotations link concepts and paper chunks to each reference. The source files contain metadata and links, not copies of the cited works.
