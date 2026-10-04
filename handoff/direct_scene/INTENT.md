# Intent

## The goal

The owner researches how to prompt AI video models. This repository should turn an ordinary ask
into a directed scene by letting an LLM reason through that research, layer by layer, and then
compile the result the same way every time into the existing canonical score and provider build.

Today the repository retrieves knowledge and resolves defaults. It does not direct. For
"A jail fight scene, 15 seconds" it returns a score marked `ready` with no characters, no beats,
no actions and no contacts. Closing that gap is the work.

## What the owner wants (rules)

1. **The LLM directs; Python does not invent.** The LLM decides who is in the scene, what happens
   in what order, how bodies move, how it is performed, how the camera shows it, how it looks and
   sounds. Python supplies each pass its context, checks each proposal, and compiles accepted
   decisions deterministically.
2. **Layers and sublayers.** Reasoning happens between the large creative passes and inside them:
   Laban Body, Effort (weight, time, space, flow), Shape and Space; Bartenieff connectivity; FACS
   events; affect; the camera's framing, angle, position, movement, movement quality, relation to
   subject, lens and focus. The sublayers of one layer are decided together as a stack so they
   fit each other. They are not isolated prompts.
3. **One shared scene state.** Accepted decisions live in one place (the scratchpad). Each is
   attached to its layer or sublayer and records: what it read, what it chose, its relative
   anchor (baseline and change), a brief justification, and its source status. Later passes read
   earlier ones. A revision cannot silently overwrite another layer's accepted decision.
4. **Research feeds every layer.** Research supplies knowledge and taste guidance for each layer
   and sublayer. Each decision links to the research it used and says briefly how it applies.
   Three things stay distinct: sourced knowledge, the LLM's creative application or invention,
   and results tested on a model. Research-backed reasoning does not turn a creative choice into
   a research finding.
5. **Relative, not absolute.** A magnitude is stated as a named anchor (a visible baseline
   earlier in the clip) and a change against it. Structured numeric controls and relative
   anchors are compatible: keep both in the scene; choose the provider's representation
   separately.
6. **Explicit where it matters.** Contact, hands, the reaction to a contact, event order, the
   end state and camera grammar are stated, not assumed.
7. **One canonical score, one compiler.** Accepted decisions land in the existing Universal
   Score and go through the existing build. No second score, compiler, workflow engine or
   roadmap.
8. **Model facts belong to models.** Prompt length limits and allowed durations come from the
   selected provider's capability file. There is no universal 2,000-character limit. A requested
   duration the provider cannot do is reported, never silently shortened.
9. **Determinism means reproducible compilation.** The same accepted decisions, repository
   version and provider configuration give the same score and build. It does not mean the LLM
   proposes the same thing twice.
10. **The natural-language output follows the owner's skeleton** (`PROMPT_SKELETON.md`):
    absolutes stated once at the top, each beat written as changes against them, cause before
    result. The LLM reasons about its action, movement, staging and camera content; accepted
    choices and visible causal mechanisms survive in the prose, rather than only in structured
    controls. Brief reasons support authoring/review and appear where the chosen layout needs them.
    Requested NL, YAML, XML, JSON and hybrid forms remain available; none becomes another authority.
11. **Fixed sets constrain declared facets, not all scene data.** The LLM selects admitted
    source/version-bound members (`REGISTRY.md`) and supplies contextual parameters and visible
    application. Preserve existing relative/evidence contracts and their admission checks.
12. **Modular and stackable, driven by intent and taste, backed by research for the scenario.**
    Applicable sourced guidance informs choices. Authored application is distinct from research
    truth; hard rules need reviewed authority/scope and cannot silently bypass protected constraints.
13. **An incomplete ask is completed, not refused.** The system asks the user what only the
    user can answer and reasons the rest, labelling what it invented.
14. **Seconds are the canonical clock.** The score holds the numbers; XML carries ordered
    mixed content when requested; YAML can author intent/inheritance. Requested formats resolve
    into one score and are projected per route. Serial boundaries and concurrent tracks differ.
15. **Evidence before claims.** A green test or a correct read-back is not a render. Nothing is
    called model-tested until the owner renders and scores it.

## Who the LLM is

The connected coding agent (Claude Code, Codex, or another client) acting through the existing
`cpcs` CLI and MCP operations. The repository does not gain a vendor LLM client.

## Success, per slice

A slice is done when its public path works through the CLI on the jail-fight ask, its positive
and negative tests pass, the full repository gate passes, existing tests are untouched and still
pass, `REQ-077` is updated with exact evidence, and the change is committed. The whole effort
succeeds as software when the admitted ask-to-prompt contract is proved. Rendered quality and
transfer need separately authorized, scoped evidence; proposed pre-code renders do not halt all slices.

## Non-goals

- A DAG or graph executor for creative reasoning.
- Pose, depth, motion-capture or reference-video conditioning.
- Promoting any knowledge to the curated tier without the owner's review.
- Changing what `cpcs.score.build` returns for callers that do not use the directing path.
- Rewriting existing tests, or renaming or forking existing owners.

## Decision rights

| Decision | Who |
|---|---|
| Creative choices inside a scene | the LLM, recorded with source status |
| Whether a proposal is admissible | Python validators |
| What becomes curated knowledge | the owner, through the existing review and promotion operations |
| Push, pull request, merge, provider spend, renders | the owner, by explicit word each time |
