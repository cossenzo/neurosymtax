# NeuroSymTax – Neuro-symbolic automated taxonomy development

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

## Tests

`python -m pytest` runs the whole method with a scripted LLM and fake sources (no network).
