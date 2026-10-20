"""Evaluation goals of Kundisch et al. (2022, Table 4), as a declarative registry.

Each goal states what the users aim to do with the taxonomy and what the designers provide (Table 4), the evaluation
method and its criteria (Step 15, TDR 20). Each criterion names a measure computed by the program, a comparison, a
fallback target (the configuration sets the defaults) that the researcher may override in the input file (Step 5), the objects it is measured on, and the
re-entry that a failure suggests (a revision before Step 10, or new evidence before Step 6).

Steps 5 and 15 build the plan from the registry (``plan``); Step 16 computes the measures (``measure``); Step 17
compares them with the targets (``assess``). Adding a goal or a criterion means adding an entry here.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .models import MISFIT, NO_INFO, Cell, DomainObject


@dataclass(frozen=True)
class Criterion:
    key: str             # measure computed in Step 16
    label: str
    comparator: str      # ">=" or "<="
    default: float       # target value (TDR 20); may be overridden in the input
    population: str      # "new": new objects of Step 16; "all": all classified objects
    remedy: str          # re-entry suggested when unmet: "10" (revise) or "6" (new evidence)
    basis: str = ""      # source of the default target


@dataclass(frozen=True)
class GoalSpec:
    name: str
    users_aim: str           # Kundisch et al. (2022), Table 4: taxonomy users aim to use the taxonomy to ...
    designers_provide: str   # ... taxonomy designers provide ...
    method: str
    criteria: tuple[Criterion, ...]


MISFITS = Criterion("misfit_share", "share of new objects with a misfit in some dimension", "<=", 0.30, "new", "6")

GOALS: dict[str, GoalSpec] = {g.name: g for g in (
    GoalSpec("describing",
             "describe a certain phenomenon",
             "characteristics and dimensions that serve as a basis to describe a certain phenomenon",
             "new objects classified in every dimension",
             (Criterion("informed_share", "share of cells of new objects with a characteristic", ">=", 0.50, "new",
                        "6"), MISFITS)),
    GoalSpec("identifying",
             "identify one specific object that represents a certain phenomenon",
             "characteristics and dimensions that serve as search criteria to identify one particular object",
             "characteristic profiles of all classified objects",
             (Criterion("distinct_profiles", "share of objects whose characteristic profile no other object has",
                        ">=", 0.60, "all", "10"),)),
    GoalSpec("classifying",
             "classify objects that represent a certain phenomenon",
             "characteristics and dimensions that serve as scheme to classify one particular object",
             "new objects classified twice, independently",
             (Criterion("kappa", "mean Cohen's kappa between the two classifications", ">=", 0.61, "new", "10",
                        "substantial agreement (Landis & Koch, 1977)"), MISFITS)),
    GoalSpec("analyzing",
             "analyze objects that represent a certain phenomenon",
             "characteristics and dimensions that serve as a basis to determine similarities and differences of "
             "objects",
             "distribution of all classified objects over the characteristics",
             (Criterion("discriminating_dimensions", "share of dimensions in which no characteristic holds more than "
                        "the dominance threshold of the informed objects", ">=", 0.60, "all", "10"),)),
    GoalSpec("clustering",
             "cluster objects based on similarities and differences to consider types of objects rather than "
             "individual objects",
             "characteristics and dimensions that serve as a basis for grouping a set of objects in such a way that "
             "objects in the same group are more similar to each other than to those in other groups",
             "agglomerative clustering of all classified objects by their characteristic profiles",
             (Criterion("cluster_silhouette", "silhouette of the best grouping (2 to 10 groups)", ">=", 0.25, "all",
                        "10", "weak but present structure (Kaufman & Rousseeuw, 1990)"),)),
)}


# --------------------------------------------------------------------------- Steps 5 and 15


def plan(goals: list[dict], defaults: dict[str, float] | None = None) -> list[dict]:
    """[S] The evaluation plan: for each goal of the input, its Table 4 entry, method and criteria with targets."""
    out = []
    for g in goals:
        spec = GOALS[g["goal"]]
        targets = g.get("targets") or {}
        out.append({"goal": spec.name, "users_aim": spec.users_aim, "designers_provide": spec.designers_provide,
                    "method": spec.method,
                    "criteria": [{"measure": c.key, "label": c.label, "comparator": c.comparator,
                                  "target": float(targets.get(c.key, (defaults or {}).get(c.key, c.default))), "population": c.population,
                                  "remedy": c.remedy, "basis": c.basis} for c in spec.criteria]})
    return out


def unknown_targets(goals: list[dict]) -> list[str]:
    return [f"{g['goal']}: {k}" for g in goals for k in (g.get("targets") or {})
            if k not in {c.key for c in GOALS[g["goal"]].criteria}]


# --------------------------------------------------------------------------- Step 16


def cohen_kappa(a: list[str], b: list[str]) -> Optional[float]:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in ca) / (n * n)
    if pe >= 1:
        return 1.0 if po == 1 else 0.0
    return (po - pe) / (1 - pe)


def _value(cells: dict[str, dict[str, Cell]], oid: str, did: str) -> str:
    return cells.get(oid, {}).get(did, Cell()).value


def _silhouette(profiles: list[tuple], max_groups: int) -> Optional[float]:
    """Best silhouette of an agglomerative grouping of the profiles (Hamming distance, average linkage)."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import silhouette_score

    n = len(profiles)
    if n < 3 or len(set(profiles)) < 2:
        return None
    cats = sorted({v for p in profiles for v in p})
    x = np.array([[cats.index(v) for v in p] for p in profiles])
    dist = (x[:, None, :] != x[None, :, :]).mean(axis=2)
    best = None
    for k in range(2, min(max_groups, n - 1) + 1):
        labels = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average").fit_predict(dist)
        if len(set(labels)) < 2:
            continue
        s = float(silhouette_score(dist, labels, metric="precomputed"))
        best = s if best is None else max(best, s)
    return best


def measure(new: list[DomainObject], first: dict[str, dict[str, Cell]], second: dict[str, dict[str, Cell]],
            all_objects: list[DomainObject], dims: list[str], dominance: float, max_groups: int) -> dict:
    """[S] Every measure of the registry. ``first`` and ``second`` are the two independent classifications of the
    new objects; ``all_objects`` are all classified objects (with their stored cells)."""
    ids = [o.id for o in new]
    n = len(ids) or 1
    kappas = {}
    for d in dims:
        k = cohen_kappa([_value(first, i, d) for i in ids], [_value(second, i, d) for i in ids])
        if k is not None:
            kappas[d] = round(k, 4)
    misfit = sum(1 for i in ids if any(_value(first, i, d) == MISFIT for d in dims))
    informed = sum(1 for i in ids for d in dims if _value(first, i, d) not in (NO_INFO, MISFIT))
    stored = {o.id: o.cells for o in all_objects}
    profiles = [tuple(stored[o.id].get(d, Cell()).value for d in dims) for o in all_objects]
    counts = Counter(profiles)
    discriminating = 0
    for j, d in enumerate(dims):
        values = [p[j] for p in profiles if p[j] not in (NO_INFO, MISFIT)]
        if len(set(values)) >= 2 and Counter(values).most_common(1)[0][1] <= dominance * len(values):
            discriminating += 1
    sil = _silhouette(profiles, max_groups)
    return {"new_objects": len(ids), "all_objects": len(all_objects),
            "kappa_per_dimension": kappas,
            "kappa": round(sum(kappas.values()) / len(kappas), 4) if kappas else None,
            "misfit_share": round(misfit / n, 4),
            "informed_share": round(informed / (n * max(len(dims), 1)), 4),
            "distinct_profiles": round(sum(1 for p in profiles if counts[p] == 1) / (len(profiles) or 1), 4),
            "discriminating_dimensions": round(discriminating / (len(dims) or 1), 4),
            "cluster_silhouette": None if sil is None else round(sil, 4)}


# --------------------------------------------------------------------------- Step 17


def assess(evaluation_plan: list[dict], measures: dict, required_new: int) -> list[dict]:
    """[S] Compare every criterion of the plan with its target. Returns one result per criterion."""
    results = []
    if measures.get("new_objects", 0) < required_new:
        results.append({"goal": "all", "measure": "new_objects", "value": measures.get("new_objects", 0),
                        "target": required_new, "comparator": ">=", "met": False, "remedy": "6"})
    for g in evaluation_plan:
        for c in g["criteria"]:
            value = measures.get(c["measure"])
            met = value is not None and (value >= c["target"] if c["comparator"] == ">=" else value <= c["target"])
            results.append({"goal": g["goal"], "measure": c["measure"], "value": value, "target": c["target"],
                            "comparator": c["comparator"], "met": met, "remedy": c["remedy"]})
    return results
