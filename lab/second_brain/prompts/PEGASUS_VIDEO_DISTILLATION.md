# Pegasus AI video-to-reasoning distillation contract

This contract augments—not replaces—`lab/RUNBOOK_pegasus_extraction.md`. For exact movement
reconstruction also follow `lab/RUNBOOK_reference_to_kinematic_truth.md`.

## Objective

Distill an authorized source video into immutable semantic observations that can support retrieval,
reasoning, comparison, and proposal generation without pretending that Pegasus measured exact
trajectories.

## Evidence boundary

Pegasus output is limited to:

```text
interpreted
inferred
```

It may describe visible or likely structure, but it is not `measured`. Pose coordinates, optical flow,
camera transforms, facial curves, word times, masks, and contact distances require named measurement
tools and separate records. When Pegasus and a measurement disagree, preserve both and resolve through
typed precedence; never overwrite either.

## Required manifest

Before extraction record:

- source URI/path and `sha256`;
- rights scope and authorized transformation scope;
- duration, nominal fps, dimensions, and source timebase when known;
- Pegasus provider, model, and model version;
- extraction schema ID/hash;
- exact prompt hash;
- pass ID and clipping interval;
- ingestion timestamp and agent version.

Dense source media and analysis artifacts remain in `work/second_brain/`.

## Pass strategy

Use the repository runbook's multipass procedure. Maintain stable entity IDs from the source-map pass
through every later pass. Each pass appends or supersedes observations; it does not silently rewrite
earlier output.

Capture:

1. sequences, scenes, shots, beats, and communication function;
2. stable actors, products, props, environments, and targets;
3. action atoms and phase landmarks;
4. gaze, facial behavior, displayed affect, gesture, body mechanics, and Laban-language qualities;
5. camera interpretation separated from visible image motion;
6. edit, retime, caption, audio, word/phoneme anchor, SFX, and VFX events;
7. contact claims typed as confirmed-looking, possible, near-contact, or ambiguous—not measured;
8. alternatives, contradictions, occlusions, uncertainty, and unsupported fields;
9. semantic signature: action order, participants/targets, contact sequence, communication function,
   shot purpose, and protected invariants.

## Time handling

Store both:

- `raw_time`: exactly what Pegasus returned in the clipped/source context;
- `resolved_time`: the time after source-clock conversion or snapping;
- `resolution_method` and `delta`.

Never discard the raw value. Do not use generated/presentation time without an explicit clock map.

## Output

Append one record per observation or bounded observation bundle conforming to
`lab/second_brain/schemas/video_observation.schema.json`.

After append:

1. validate schema and hash chain;
2. run contradiction checks;
3. link source-video and entity IDs;
4. generate proposals for reusable concepts, authored relationships, intents, mappings, rules, or
   failure modes;
5. deduplicate proposals against `lab/concepts.jsonl`;
6. leave proposals pending until deliberate promotion.

Pegasus may add evidence that a concept occurs in a source video. It cannot prove that a control
improves generation. Provider-effect weights require immutable render experiments.

## Required honest-limits report

Every extraction batch ends with:

```text
What Pegasus observed semantically
What was inferred rather than visible
What could not be resolved
What requires measurement
What source-clock transformations were applied
What reusable proposals were emitted
What rights or identity fields must be excluded or replaced
```
