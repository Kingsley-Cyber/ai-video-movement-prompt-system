# WP-5 — TreatmentAdapter integration (bridge -> typed controls)

Depends on: WP-4 (and WP-6 for the structured interaction payload).

## Scope

Modify `lab/application/reasoning_treatment.py` — ONE new pass only:

```
translate(packet):
    application_set = apply_knowledge(...)      # NEW
    for decision in application_set.decisions:  # NEW routing
        CONTROL      -> existing registry constructor (existing path)
        VERIFICATION -> translation.verification_requirements
        PLANNING     -> translation.planning_guidance (NEW field)
        NON_EXECUTABLE -> translation.reasoning_material (NEW field)
    ... existing overlay/structured paths UNCHANGED ...
```

- New `Translation` fields: `planning_guidance`, `reasoning_material`,
  `application_set` (additive; old fields keep identical behavior).
- Guided finish package already carries translation objects alongside the
  score — planning_guidance and reasoning_material flow there too; they NEVER
  enter the resolved score (score_id integrity).
- Update `cpcs_guided_handlers._finish` final_prompt_package to include
  `knowledge_application` summary (counts per decision type + pack ids).

## Acceptance tests (`test_ka1_adapter.py`)

- ecommerce pack CONTROL -> a structured object appears with lineage
  requirement_ids + evidence_ids (IDs only).
- VERIFICATION decision -> verification_requirements entry (schema-valid:
  metric_id/target_paths/method/observability/source_profile).
- PLANNING / NON_EXECUTABLE decisions -> appear ONLY in planning_guidance /
  reasoning_material; assert they are absent from overlays, structured
  objects, provider_neutral_controls, and verification.
- regression: run all pre-KA suites (listed in master brief §5) — must pass
  unchanged semantics.
- D4: no pack prose anywhere in translation outputs.

## Forbidden

- No changes to `compile_build` / `resolve_score` / Control A.
- No post-resolution score mutation.

## Done when

`test_ka1_adapter.py` passes and all pre-KA suites are green.
