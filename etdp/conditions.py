"""[S] Objective ending conditions (Steps 11–12): O1–O3, O5–O8 and O10 are checked; O5 only after an empirical-to-
conceptual (e) iteration that is not the first; O4 (no dimension or characteristic added) is not applied; O9 (mutually
exclusive and collectively exhaustive) is a rule given to the LLM and is not checked."""

from __future__ import annotations

from collections import Counter

from .config import AppConfig
from .models import MISFIT, Cell, RunState
from .operations import RESTRUCTURING, norm

CONDITIONS = {
    "O1": "All objects examined",
    "O2": "No object merged or split in the last iteration",
    "O3": "At least one object under every characteristic",
    "O5": "No dimension or characteristic merged or split in the last empirical-to-conceptual (e) iteration (not the first)",
    "O6": "Every dimension unique",
    "O7": "Every characteristic unique within its dimension",
    "O8": "Every cell unique",
    "O9": "Mutually exclusive and collectively exhaustive (a rule given to the LLM; not checked)",
    "O10": "Structure",
}


def objective(state: RunState, cfg: AppConfig) -> tuple[dict[str, bool], dict[str, str], list[str]]:
    """Evaluate the checked conditions on the taxonomy, the classification matrix (building objects) and the
    operations of the current iteration. Returns (holds, details, open issues). O9 is not among the holds."""
    tax, objs = state.taxonomy, state.building_objects()
    ops = state.current.operations if state.iterations else []
    ok: dict[str, bool] = {}
    det: dict[str, str] = {}
    issues: list[str] = []

    stale = [o.id for o in objs for d in tax.dimensions if o.cells.get(d.id, Cell()).key != d.signature()]
    ok["O1"] = bool(tax.dimensions) and bool(objs) and not stale
    det["O1"] = (f"{len(objs)} objects, {len(tax.dimensions)} dimensions; "
                 f"{len(set(stale))} objects not classified in every dimension")
    if not ok["O1"]:
        issues.append("O1: " + ("the taxonomy has no dimension" if not tax.dimensions else
                                "no object" if not objs else f"objects not yet classified: {sorted(set(stale))}"))

    ok["O2"] = True
    det["O2"] = "objects are registered once and never merged or split"

    # Exempt: conceptual characteristics (TDR 19) and negation characteristics, which close a dimension so that it
    # is collectively exhaustive (TDR 18) and need no object of their own.
    empty, exempt = [], []
    for d in tax.dimensions:
        for c in d.characteristics:
            if not any(o.cells.get(d.id, Cell()).value == c.id for o in objs):
                (exempt if c.origin == "conceptual" or c.negation else empty).append(f"{c.id} '{c.name}'")
    ok["O3"] = not empty
    det["O3"] = (f"{len(empty)} characteristics without objects" +
                 (f"; conceptual or negation, exempt: {', '.join(exempt)}" if exempt else ""))
    issues += [f"O3: characteristic {e} has no object" for e in empty]

    # O5 concerns only the empirical-to-conceptual (e) iterations after the first, which change the taxonomy on the
    # basis of new objects. The conceptual-to-empirical (c) iterations and the revisions adjust the taxonomy on purpose
    # and are not checked. O4 is not applied: an e iteration may add elements for what the new objects show; the
    # subjective conditions (Steps 13–14) and the evaluation with new objects (Steps 15–16) judge the result.
    empirical = bool(state.iterations) and state.current.kind == "e" and \
        sum(1 for r in state.iterations if r.kind == "e") > 1
    restructured = [lg for lg in ops if lg.op in RESTRUCTURING]
    skipped = "not checked: only the e iterations after the first are checked"
    ok["O5"] = not (empirical and restructured)
    det["O5"] = f"{len(restructured)} merges or splits in this e iteration" if empirical else skipped

    names = Counter(norm(d.name) for d in tax.dimensions)
    dup_dims = [n for n, k in names.items() if k > 1]
    ok["O6"] = not dup_dims
    det["O6"] = "no duplicate dimension" if not dup_dims else f"duplicate dimensions: {dup_dims}"
    issues += [f"O6: duplicate dimension name '{n}'" for n in dup_dims]

    dup_chars = [f"{d.id}: {n}" for d in tax.dimensions
                 for n, k in Counter(norm(c.name) for c in d.characteristics).items() if k > 1]
    ok["O7"] = not dup_chars
    det["O7"] = "no duplicate characteristic within a dimension" if not dup_chars else f"duplicates: {dup_chars}"
    issues += [f"O7: duplicate characteristic {x}" for x in dup_chars]

    across = Counter(norm(c.name) for d in tax.dimensions for c in d.characteristics)
    repeated = [n for n, k in across.items() if k > 1]
    ok["O8"] = not repeated
    det["O8"] = "no characteristic repeated across dimensions" if not repeated else f"repeated: {repeated}"
    issues += [f"O8: characteristic name '{n}' repeated across dimensions" for n in repeated]

    # O9 is not checked: it is a rule given to the LLM. The misfits are only reported.
    misfits = sum(1 for o in objs for d in tax.dimensions
                  if (c := o.cells.get(d.id)) is not None and c.key == d.signature() and c.value == MISFIT)
    det["O9"] = f"not checked; reported: {misfits} misfits"

    m = cfg.method
    structure = []
    for p in state.input.perspective_names:
        n = sum(1 for d in tax.dimensions if norm(d.perspective) == norm(p))
        if n < m.min_dimensions_per_perspective:
            structure.append(f"O10: perspective '{p}' has {n} dimension(s); at least {m.min_dimensions_per_perspective}")
    for d in tax.dimensions:
        if len(d.characteristics) < m.min_characteristics_per_dimension:
            structure.append(f"O10: dimension {d.id} '{d.name}' has {len(d.characteristics)} characteristic(s)")
    ok["O10"] = not structure
    det["O10"] = "; ".join(s[5:] for s in structure) or "structure rules hold"
    issues += structure
    return ok, det, issues


