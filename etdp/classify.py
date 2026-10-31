"""Procedure Classify: [N] the LLM classifies objects in dimensions (and, in Step 8e, codes the characteristics the
taxonomy lacks); [S] the answers are checked against the taxonomy (a value that is not a characteristic of the
dimension, "misfit" or "no_information" becomes "no_information")."""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Optional

from .models import MISFIT, NO_INFO, Cell, Code, Dimension, DomainObject, ExamOut, Taxonomy

if TYPE_CHECKING:
    from .context import Context

logger = logging.getLogger(__name__)


def taxonomy_view(dims: list[Dimension]) -> list[dict]:
    return [{"id": d.id, "name": d.name, "definition": d.definition, "perspective": d.perspective,
             "application_rule": d.application_rule,
             "characteristics": [{"id": c.id, "name": c.name, "definition": c.definition,
                                  **({"negation": True} if c.negation else {})} for c in d.characteristics]}
            for d in dims]


def object_view(obj: DomainObject, limit: int) -> dict:
    return {"id": obj.id, "name": obj.name, "description": obj.description,
            "passages": [e.quote for e in obj.evidence[:limit]]}


def stale_dimensions(obj: DomainObject, tax: Taxonomy) -> list[Dimension]:
    """Dimensions in which ``obj`` must be classified again (R7): its cell is missing, the structure of the dimension
    changed, or the wording changed and the cell names no characteristic. A cell that names a characteristic survives
    a change of wording and is only marked with the new wording."""
    stale = []
    for d in tax.dimensions:
        c = obj.cells.get(d.id)
        if c is None or c.key != d.signature():
            stale.append(d)
        elif c.text != d.wording():
            if c.value in (MISFIT, NO_INFO):
                stale.append(d)
            else:
                c.text = d.wording()
    return stale


def _cell(dim: Dimension, out) -> Cell:
    """[S] The classification of one object in one dimension; an invalid answer is "no_information"."""
    cell = Cell(key=dim.signature(), text=dim.wording())
    if out is not None and out.value in {c.id for c in dim.characteristics} | {MISFIT, NO_INFO}:
        cell.value = out.value
    return cell


def examine(ctx: "Context", tax: Taxonomy, objects: list[DomainObject], coding: bool = False, store: bool = True,
            only_stale: bool = True, variant: Optional[int] = None) -> tuple[dict[str, dict[str, Cell]], list[Code]]:
    """Classify ``objects`` in ``tax`` (only in stale dimensions when ``only_stale``) and, with ``coding``, code the
    characteristics relevant to the meta-characteristic that the taxonomy lacks. ``variant`` shuffles the order of
    objects and dimensions (independent second classification). Returns the cells and the codes; with
    ``store`` the cells are written to the objects."""
    st, m = ctx.state, ctx.cfg.method
    rng = random.Random(variant) if variant is not None else None
    todo = []
    for o in objects:
        dims = stale_dimensions(o, tax) if only_stale else list(tax.dimensions)
        if dims or coding:
            todo.append((o, dims))
    if rng:
        rng.shuffle(todo)
    cells: dict[str, dict[str, Cell]] = {}
    codes: list[Code] = []
    n_cells = 0
    size = m.classification_batch_size
    for i in range(0, len(todo), size):
        batch = todo[i: i + size]
        dims = [d for d in tax.dimensions if any(d in ds for _, ds in batch)]
        if rng:
            rng.shuffle(dims)
        variables = {**ctx.base_vars(), "taxonomy": taxonomy_view(dims) if dims else "none",
                     "objects": [object_view(o, ctx.cfg.documents.passages_per_object) for o, _ in batch],
                     "coding": "yes" if coding else "no"}
        out = ctx.llm.structured("classify_objects", variables, ExamOut)
        answers = {a.object_id: a for a in out.objects}
        for o, _ in batch:
            ans = answers.get(o.id)
            by_dim = {c.dimension_id: c for c in (ans.cells if ans else [])}
            cells[o.id] = {}
            for d in dims:
                cells[o.id][d.id] = _cell(d, by_dim.get(d.id))
                n_cells += 1
            if coding and ans:
                for c in ans.codes:
                    if c.label.strip():
                        codes.append(Code(id=f"X{st.next_code}", object_id=o.id, label=c.label.strip(),
                                          definition=c.definition))
                        st.next_code += 1
            if store:
                o.cells.update(cells[o.id])
    if store and st.iterations:
        st.current.cells_classified += n_cells
    logger.info("classified %d cells; %d codes", n_cells, len(codes))
    return cells, codes


def drop_removed(objects: list[DomainObject], tax: Taxonomy) -> None:
    ids = {d.id for d in tax.dimensions}
    for o in objects:
        for k in [k for k in o.cells if k not in ids]:
            del o.cells[k]
