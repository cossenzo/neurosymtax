"""Single-prompt baseline: one request asks the LLM for a complete taxonomy designed with the ETDP; no document is
retrieved and no rule is applied. The structure of the answer is then checked with the same symbolic rules (O6–O8,
O10 and R5), for comparison only."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import AppConfig, InputSpec
from .llm import LLMClient, create_llm
from .models import BaselineOut, Characteristic, Dimension, Taxonomy
from .operations import invariants


def to_taxonomy(out: BaselineOut) -> Taxonomy:
    tax = Taxonomy()
    for spec in out.dimensions:
        did = tax.new_dimension_id()
        tax.dimensions.append(Dimension(
            id=did, name=spec.name, definition=spec.definition, application_rule=spec.application_rule,
            perspective=spec.perspective, origin="conceptual",
            characteristics=[Characteristic(id=tax.new_characteristic_id(did), name=c.name, definition=c.definition,
                                            negation=c.negation, origin="conceptual") for c in spec.characteristics]))
    return tax


def run_baseline(cfg: AppConfig, inp: InputSpec, output_dir: Optional[str] = None, run_id: Optional[str] = None,
                 llm: Optional[LLMClient] = None) -> Path:
    llm = llm or create_llm(cfg.llm, log_prompts=cfg.output.log_prompts)
    run_id = run_id or "baseline-" + datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = Path(output_dir or cfg.output.dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    variables = {"phenomenon": inp.phenomenon, "users": inp.users, "purpose": inp.purpose,
                 "domain_of_objects": inp.domain_of_objects, "perspectives": inp.perspective_names,
                 "meta_characteristic": inp.meta_characteristic or "none (determine it)", "language": inp.language,
                 "min_dimensions_per_perspective": cfg.method.min_dimensions_per_perspective,
                 "min_characteristics_per_dimension": cfg.method.min_characteristics_per_dimension}
    out = llm.structured("baseline", variables, BaselineOut)
    tax = to_taxonomy(out)
    counts = {p: sum(1 for d in tax.dimensions if d.perspective.casefold() == p.casefold())
              for p in inp.perspective_names}
    problems = invariants(tax, inp, cfg) + [f"perspective '{p}' has {n} dimension(s)" for p, n in counts.items()
                                            if n < cfg.method.min_dimensions_per_perspective]
    doc = {"run_id": run_id, "configuration": "single-prompt baseline", "meta_characteristic": out.meta_characteristic,
           "dimensions": [d.model_dump(include={"id", "name", "definition", "application_rule", "perspective",
                                                "characteristics"}) for d in tax.dimensions],
           "structure_problems": problems, "tokens_used": llm.tokens_used}
    (run_dir / "taxonomy.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_dir
