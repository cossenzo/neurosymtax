"""[S] Step 18 – Report: taxonomy (JSON and Markdown), classification matrix, operations log, iterations, sources
and an audit of the symbolic decisions (TDR 24–26)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import AppConfig
from .models import MISFIT, NO_INFO, Cell, RunState


def _json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _order(oid: str) -> int:
    return int(oid[1:]) if oid[1:].isdigit() else 0


def taxonomy_document(st: RunState) -> dict:
    objs = st.building_objects()
    last = st.iterations[-1] if st.iterations else None
    dims = []
    for d in st.taxonomy.dimensions:
        dims.append({"id": d.id, "name": d.name, "definition": d.definition, "application_rule": d.application_rule,
                     "perspective": d.perspective, "origin": d.origin,
                     "characteristics": [{"id": c.id, "name": c.name, "definition": c.definition, "negation": c.negation,
                                          "origin": c.origin,
                                          "objects": sum(1 for o in objs if o.cells.get(d.id, Cell()).value == c.id)}
                                         for c in d.characteristics]})
    return {
        "run_id": st.run_id, "status": st.status, "message": st.message,
        "input": st.input.model_dump(), "meta_characteristic": st.meta_characteristic,
        "iterations": len(st.iterations), "documents_read": sum(1 for d in st.documents.values()
                                                                if d.status == "processed"),
        "objects": {"building": len(objs), "evaluation": sum(1 for o in st.objects.values() if o.role == "evaluation")},
        "perspectives": {p: [d["id"] for d in dims if d["perspective"] == p] for p in st.input.perspective_names},
        "dimensions": dims,
        "objective_conditions": {"holds": last.objective, "details": last.objective_details} if last else {},
        "subjective_conditions": last.subjective if last else {},
        "evaluation_plan": st.evaluation_plan, "evaluation": st.evaluation,
        "open_issues": st.issues, "tokens_used": st.tokens_used,
    }


def taxonomy_markdown(st: RunState) -> str:
    lines = [f"# Taxonomy: {st.input.phenomenon}", "", f"Meta-characteristic: {st.meta_characteristic}", "",
             f"Status: {st.status}. {st.message}", ""]
    for p in st.input.perspective_names:
        lines += [f"## {p}", "", "| Dimension | Characteristics |", "|---|---|"]
        for d in st.taxonomy.dimensions:
            if d.perspective == p:
                chars = "; ".join(f"{c.name}{' (conceptual)' if c.origin == 'conceptual' else ''}"
                                  for c in d.characteristics)
                lines.append(f"| {d.name} | {chars} |")
        lines.append("")
    lines += ["## Definitions", ""]
    for d in st.taxonomy.dimensions:
        lines += [f"**{d.name}** ({d.perspective}). {d.definition} *Application rule:* {d.application_rule}", ""]
        lines += [f"- *{c.name}*: {c.definition}" for c in d.characteristics] + [""]
    return "\n".join(lines)


def audit_document(st: RunState) -> dict:
    return {
        "iterations": [{"number": r.number, "kind": r.kind, "reason": r.reason, "queries": r.queries,
                        "documents": len(r.documents), "new_objects": len(r.new_objects),
                        "codes": r.codes,
                        "concepts": r.concepts, "proposal_attempts": r.attempts, "proposal_rejected": r.rejected,
                        "operations": [f"{o.op} {o.targets or o.created}" for o in r.operations],
                        "cells_classified": r.cells_classified,
                        "meta_review": r.meta_review,
                        "objective_unmet": [k for k, v in r.objective.items() if not v],
                        "subjective_unmet": [k for k, v in r.subjective.items() if not v["passed"]],
                        "evaluation": {k: v for k, v in r.evaluation.items() if k != "new_object_ids"},
                        "exit": r.exit, "entry": r.entry,
                        "entry_reason": r.entry_reason, "tokens": r.tokens}
                       for r in st.iterations],
        "tokens": {"total": st.tokens_used, "by_step": st.tokens_by_step, "by_task": st.tokens_by_task},
    }


def write_outputs(st: RunState, run_dir: str | Path, cfg: AppConfig) -> None:
    out = Path(run_dir)
    out.mkdir(parents=True, exist_ok=True)
    _json(out / "taxonomy.json", taxonomy_document(st))
    (out / "taxonomy.md").write_text(taxonomy_markdown(st), encoding="utf-8")
    _json(out / "operations.json", [o.model_dump() for o in st.operations_log])
    _json(out / "iterations.json", [r.model_dump() for r in st.iterations])
    _json(out / "sources.json", [d.model_dump() for d in st.documents.values()])
    _json(out / "audit.json", audit_document(st))
    _json(out / "objects.json", [o.model_dump() for o in sorted(st.objects.values(), key=lambda o: _order(o.id))])
    with (out / "objects_matrix.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["object_id", "object", "role"] + [f"{d.id} {d.name}" for d in st.taxonomy.dimensions])
        for o in sorted(st.objects.values(), key=lambda o: _order(o.id)):
            row = [o.id, o.name, o.role]
            for d in st.taxonomy.dimensions:
                v = o.cells.get(d.id, Cell()).value
                c = d.characteristic(v)
                row.append(c.name if c else ("misfit" if v == MISFIT else "no information" if v == NO_INFO else v))
            w.writerow(row)
