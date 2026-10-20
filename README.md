# NeuroSymTax: Neuro-Symbolic Automated Taxonomy Development with Applications in Decentralized Finance

Automates the extended taxonomy design process (ETDP) of Kundisch et al. (2022). Each step is done by the researcher
[I], the LLM or the embedding model [N], or program code [S]. The LLM proposes; the program verifies and decides.

## Installation

```
python -m pip install -r requirements.txt
copy .env.example .env        # then fill in the keys you use; never share .env
```

Keys (only in `.env`): the LLM provider's key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `GEMINI_API_KEY`),
`TAVILY_API_KEY` for web search, and optionally `SEMANTIC_SCHOLAR_API_KEY`. Set `llm.model` in `config.yaml`.

## Running

```
python -m etdp run --input input_defi.yaml --config config.yaml            # full approach
python -m etdp run --input input_defi.yaml --config config_ablation.yaml   # ablation
python -m etdp baseline --input input_defi.yaml --config config.yaml       # single-prompt baseline
python -m etdp resume --run-id <run id>                                    # continue an interrupted run
```

Console and `run.log`: the objective conditions that fail and why, the subjective conditions that fail with the judge's justification and suggestions, and, for every proposal of operations, the rules it violates (R5: broken invariant of the taxonomy), each violation and the correction requested.

Outputs (`output/<run id>/`): `taxonomy.json` and `taxonomy.md` (perspectives, dimensions, characteristics,
definitions, objects per characteristic), `objects_matrix.csv` (classification matrix), `operations.json`
(every operation with iteration and evidence), `iterations.json`, `audit.json` (approach and re-entry decisions,
proposal attempts and violations, conditions per iteration, tokens), `objects.json`, `sources.json`, `run.log`
(every prompt and answer) and `state.json` (checkpoint after every step).

## Input (Steps 1–3, [I])

`input.yaml`: `observed_phenomenon`, `target_user_groups`, `intended_purposes`, `purpose_type`
(`structuring` | `identification_and_structuring`), `purpose_nature` (`descriptive` | `normative`),
`domain_of_objects`, `evaluation_goals`, `perspectives`, optional `meta_characteristic`, `seed_keywords`, `language`,
`year_range`. See `input.example.yaml` and `input_defi.yaml`.

## Evaluation goals (Kundisch et al., 2022, Table 4)

The goals are a registry in `etdp/goals.py`: each goal has its Table 4 entry, method and criteria; each criterion
names a measure, a default target, the objects it is measured on (new or all) and the re-entry its failure suggests
(a revision before Step 10, or new evidence before Step 6). The input chooses the goals and may override targets:

```yaml
evaluation_goals:
  - goal: classifying                 # defaults: kappa >= 0.61, misfit_share <= 0.30 (defaults: `evaluation.targets` in config.yaml)
    targets: {kappa: 0.61, misfit_share: 0.30}
  - goal: identifying
    targets: {distinct_profiles: 0.7}
```

| Goal | Criteria (default target) |
|---|---|
| describing | informed_share (>= 0.50), misfit_share (<= 0.30) |
| identifying | distinct_profiles (>= 0.80) |
| classifying | kappa (>= 0.61), misfit_share (<= 0.30) |
| analyzing | discriminating_dimensions (>= 0.60; dominance threshold 0.9 in config) |
| clustering | cluster_silhouette (>= 0.25; 2 to `max_groups` groups) |

Step 5 builds the plan from the registry; Step 16 computes the measures; Step 17 compares each with its target
(`taxonomy.json` → `evaluation.results`). A new goal or criterion is a new registry entry.

## Steps and rules

| Step | Code (`etdp/steps.py`) |
|---|---|
| 1–3 | [I] input; [S] validated |
| 4 | [N] meta-characteristic if not given; reviewed once after the first iteration, whatever its type; [S] a refinement is accepted only if it is not further from the domain of objects (R4) |
| 5 | [S] objective conditions (O1–O8, O10; O9 is a rule given to the LLM), subjective conditions; evaluation method, criterion, target per goal |
| 6 | [S] approach by R1–R3 (ablation: [N]) |
| 7e–9e | [N] search string of 2–5 broad keywords for objects not yet registered (never for particular characteristics); [S] scholarly full texts (if too few are found, only the search string is relaxed, to its first 4 and then 2 keywords; the year range and open access always apply) + web pages (counts in `config.yaml`), each read in full; [N] objects; [S] registration: the named objects whose name occurs in the text read are registered, the characteristics of the new objects are reported by the LLM, `objects_per_description` objects per call, and stored as a document of the run; [S] the passages most relevant to the taxonomy; [N] classification and coding; [N] operations; [S] verification and correction (R5) |
| 7c–8c | [N] search string addressing the open issues; [S] retrieval, each document read in full; [N] concepts; [N] operations; [S] verification; [N] classification in the new dimensions |
| 10 | [S] operations applied with permanent ids and logged; on re-entry, [N] operations resolving the open issues; a revision creates no dimension or characteristic without objects: the LLM is told so, and [S] a characteristic that a revision created and no object has is removed again, with a dimension left with too few (R6); only the cells of changed dimensions are classified again (R7) |
| 11–12 | [S] O1–O3, O5–O8 and O10 (`conditions.py`); O5 only after an empirical-to-conceptual (e) iteration other than the first; O4 (no element added) is not applied, since Steps 13–17 judge the result; required even if all hold: meta-characteristic reviewed (R4) and an iteration of each approach (R2), else re-entry before Step 4 or Step 6; O9 (mutually exclusive and collectively exhaustive) is not checked, it is a rule in the prompts; conceptual and negation characteristics need no object (O3) |
| 13–14 | [N] one judge (taxonomy designer) that fails a condition only for relevant or serious problems, sees its previous verdict and the operations applied since; [S] unmet conditions and suggestions become open issues (R8) |
| 15–17 | [N][S] new objects classified twice; [S] criteria of the goals (`goals.py`) against their targets (R9) |
| 18 | [S] report (`export.py`) |
| re-entry | after Steps 12, 14, 17: [S] the meta-characteristic is reviewed once (R4); otherwise [N] the LLM chooses a new building iteration (before Step 6) or a revision (before Step 10); [S] stop after 15 iterations |

Operations (`operations.py`): add_dimension, add_characteristic, rename, swap, split, merge, promote, demote,
delete (Kundisch et al., 2022, Table 5). Each operation lists the evidence that justifies it (objects, concepts or open issues, whose ids
`I<iteration>.<n>` are stable); the evidence is recorded, not verified. An operation that cannot be executed (unknown
target, missing name) is skipped and logged, not corrected. A negation characteristic names a stated absence, and the LLM
is told not to delete it; no characteristic may express missing information, which is the cell value `no_information`
(R5).

## Ablation

`config_ablation.yaml` differs only in `method`: `symbolic_approach` and `verify_operations` set to `false`. Sources, flow, limits and ending conditions are the same.

## Tests

`python -m pytest` runs the whole method with a scripted LLM and fake sources (no network).
