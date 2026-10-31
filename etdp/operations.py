"""[S] Taxonomy operations (Kundisch et al., 2022, Table 5; TDR 16) and the invariants of rule R5.

The LLM proposes a list of operations; ``apply_operations`` executes them on a copy of the taxonomy. An operation that
cannot be executed (an unknown target, a missing name) is skipped and reported, not corrected. With ``check`` on (R5),
the invariants of the result are verified and the violations are returned (no characteristic may express missing
information, which is the value "no_information" of a cell); with ``check`` off (ablation), nothing is verified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .config import AppConfig, InputSpec
from .models import CharSpec, Characteristic, DimSpec, Dimension, OperationLog, OperationOut, Taxonomy

RULES = {
    "R5": "the resulting taxonomy must keep its invariants: every dimension in one perspective of the input, at least "
          "the minimum number of characteristics per dimension, at most one negation characteristic per dimension, "
          "unique and present names, and no characteristic that expresses missing information",
}
RESTRUCTURING = {"split", "merge"}                                          # O5
_VERBS = r"(?:stated|mentioned|specified|disclosed|described|reported|named|given|provided|available|known)"
_MISSING = re.compile(rf"\bnot\s+{_VERBS}\b|^\s*no\b.*\b{_VERBS}\s*$|\b(?:unspecified|unknown|unclear|n/a)\b",
                      re.IGNORECASE)


def missing_information(name: str) -> bool:
    """A characteristic named after missing information ("No segment stated", "Unknown")."""
    return bool(_MISSING.search(name or ""))


class OperationError(ValueError):
    pass


@dataclass
class Result:
    taxonomy: Taxonomy
    logs: list[OperationLog] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)        # operations that could not be executed


def norm(text: str) -> str:
    return " ".join((text or "").split()).casefold()


def canonical_perspective(value: str, perspectives: list[str]) -> Optional[str]:
    return next((p for p in perspectives if norm(p) == norm(value)), None)


def invariants(tax: Taxonomy, inp: InputSpec, cfg: AppConfig) -> list[str]:
    """R5: each dimension in exactly one perspective of the input, each characteristic in one dimension (by
    construction), at least ``min_characteristics_per_dimension`` characteristics per dimension, at most one negation
    characteristic per dimension, names present and unique."""
    problems = []
    perspectives = inp.perspective_names
    seen_dims: dict[str, str] = {}
    seen_chars: dict[str, str] = {}
    for d in tax.dimensions:
        label = f"{d.id} '{d.name}'"
        if not d.name.strip():
            problems.append(f"dimension {d.id} has no name")
        if canonical_perspective(d.perspective, perspectives) is None:
            problems.append(f"dimension {label} has perspective '{d.perspective}'; it must be one of {perspectives}")
        if len(d.characteristics) < cfg.method.min_characteristics_per_dimension:
            problems.append(f"dimension {label} has {len(d.characteristics)} characteristic(s); at least "
                            f"{cfg.method.min_characteristics_per_dimension} are required")
        if sum(c.negation for c in d.characteristics) > 1:
            problems.append(f"dimension {label} has more than one negation characteristic")
        if norm(d.name) in seen_dims:
            problems.append(f"dimensions {seen_dims[norm(d.name)]} and {d.id} have the same name")
        seen_dims.setdefault(norm(d.name), d.id)
        for c in d.characteristics:
            if not c.name.strip():
                problems.append(f"characteristic {c.id} has no name")
            elif missing_information(c.name):
                problems.append(f"characteristic {c.id} '{c.name}' expresses missing information, which is recorded as "
                                f"no_information; a negation characteristic names a stated absence (e.g. 'No "
                                f"governance: immutable contracts')")
            elif norm(c.name) in seen_chars:
                problems.append(f"characteristics {seen_chars[norm(c.name)]} and {c.id} have the same name; names must "
                                f"be unique in the taxonomy")
            seen_chars.setdefault(norm(c.name), c.id)
    return problems


class _Executor:
    def __init__(self, tax: Taxonomy, inp: InputSpec, iteration: int, origin: str) -> None:
        self.tax = tax.model_copy(deep=True)
        self.inp, self.iteration, self.origin = inp, iteration, origin

    # ------------------------------------------------------------------ helpers
    def _perspective(self, value: str, fallback: str = "") -> str:
        p = canonical_perspective(value, self.inp.perspective_names)
        if p is None and value.strip():
            return value.strip()           # a perspective outside the input is an invariant violation (R5)
        return p or fallback

    def _char(self, did: str, spec: CharSpec, derived: list[str]) -> Characteristic:
        if not spec.name.strip():
            raise OperationError("a characteristic has no name")
        return Characteristic(id=self.tax.new_characteristic_id(did), name=spec.name.strip(), definition=spec.definition,
                              negation=spec.negation, origin=self.origin, derived_from=derived, iteration=self.iteration)

    def _dimension(self, spec: DimSpec, derived: list[str]) -> Dimension:
        if not spec.name.strip():
            raise OperationError("a dimension has no name")
        if not spec.characteristics:
            raise OperationError(f"dimension '{spec.name}' has no characteristic")
        did = self.tax.new_dimension_id()
        dim = Dimension(id=did, name=spec.name.strip(), definition=spec.definition,
                        application_rule=spec.application_rule, perspective=self._perspective(spec.perspective),
                        origin=self.origin, derived_from=derived, iteration=self.iteration)
        dim.characteristics = [self._char(did, c, []) for c in spec.characteristics]
        return dim

    def _dim(self, did: str) -> Dimension:
        d = self.tax.dimension(did)
        if d is None:
            raise OperationError(f"{did} is not a dimension of the taxonomy")
        return d

    def _target(self, op: OperationOut, n: int) -> list[str]:
        if len(op.target) < n:
            raise OperationError(f"needs {n} target id(s), got {op.target}")
        return op.target

    # ------------------------------------------------------------------ operations
    def run(self, op: OperationOut) -> OperationLog:
        before = self.tax.element_ids()
        targets = getattr(self, "_" + op.op)(op)
        after = self.tax.element_ids()
        return OperationLog(iteration=self.iteration, op=op.op, targets=targets, created=sorted(after - before),
                            removed=sorted(before - after), evidence=op.evidence, reason=op.reason)

    def _add_dimension(self, op: OperationOut) -> list[str]:
        self.tax.dimensions.append(self._dimension(
            DimSpec(name=op.name, definition=op.definition, application_rule=op.application_rule,
                    perspective=op.perspective, characteristics=op.characteristics), []))
        return []

    def _add_characteristic(self, op: OperationOut) -> list[str]:
        d = self._dim(self._target(op, 1)[0])
        d.characteristics.append(self._char(d.id, CharSpec(name=op.name, definition=op.definition,
                                                           negation=op.negation), []))
        return [d.id]

    def _rename(self, op: OperationOut) -> list[str]:
        tid = self._target(op, 1)[0]
        d = self.tax.dimension(tid)
        if d is not None:
            d.name = op.name.strip() or d.name
            d.definition = op.definition or d.definition
            d.application_rule = op.application_rule or d.application_rule
            d.perspective = self._perspective(op.perspective, d.perspective) if op.perspective else d.perspective
            return [tid]
        _, c = self.tax.locate(tid)
        if c is None:
            raise OperationError(f"{tid} is not an element of the taxonomy")
        c.name = op.name.strip() or c.name
        c.definition = op.definition or c.definition
        return [tid]

    def _swap(self, op: OperationOut) -> list[str]:
        a, b = self._target(op, 2)[:2]
        dims = self.tax.dimensions
        ia = next((i for i, d in enumerate(dims) if d.id == a), None)
        ib = next((i for i, d in enumerate(dims) if d.id == b), None)
        if ia is not None and ib is not None:
            dims[ia], dims[ib] = dims[ib], dims[ia]
            return [a, b]
        da, _ = self.tax.locate(a)
        db, _ = self.tax.locate(b)
        if da is None or da is not db:
            raise OperationError("swap needs two dimensions or two characteristics of the same dimension")
        chars = da.characteristics
        i, j = [k for k, c in enumerate(chars) if c.id in (a, b)]
        chars[i], chars[j] = chars[j], chars[i]
        return [a, b]

    def _split(self, op: OperationOut) -> list[str]:
        tid = self._target(op, 1)[0]
        d = self.tax.dimension(tid)
        if d is not None:
            if len(op.parts) < 2:
                raise OperationError("splitting a dimension needs at least two parts")
            pos = self.tax.dimensions.index(d)
            new = [self._dimension(p, [tid]) for p in op.parts]
            self.tax.dimensions[pos: pos + 1] = new
            return [tid]
        d, c = self.tax.locate(tid)
        if c is None:
            raise OperationError(f"{tid} is not an element of the taxonomy")
        if len(op.characteristics) < 2:
            raise OperationError("splitting a characteristic needs at least two characteristics")
        pos = d.characteristics.index(c)
        d.characteristics[pos: pos + 1] = [self._char(d.id, s, [tid]) for s in op.characteristics]
        return [tid]

    def _merge(self, op: OperationOut) -> list[str]:
        ids = self._target(op, 2)
        if all(self.tax.dimension(i) is not None for i in ids):
            spec = DimSpec(name=op.name, definition=op.definition, application_rule=op.application_rule,
                           perspective=op.perspective or self.tax.dimension(ids[0]).perspective,
                           characteristics=op.characteristics)
            pos = min(self.tax.dimensions.index(self.tax.dimension(i)) for i in ids)
            new = self._dimension(spec, list(ids))
            self.tax.dimensions = [d for d in self.tax.dimensions if d.id not in ids]
            self.tax.dimensions.insert(min(pos, len(self.tax.dimensions)), new)
            return list(ids)
        owners = {self.tax.locate(i)[0].id if self.tax.locate(i)[0] else None for i in ids}
        if None in owners or len(owners) != 1:
            raise OperationError("merge needs dimensions, or characteristics of one dimension")
        d = self.tax.dimension(owners.pop())
        pos = min(k for k, c in enumerate(d.characteristics) if c.id in ids)
        new = self._char(d.id, CharSpec(name=op.name, definition=op.definition, negation=op.negation), list(ids))
        d.characteristics = [c for c in d.characteristics if c.id not in ids]
        d.characteristics.insert(min(pos, len(d.characteristics)), new)
        return list(ids)

    def _promote(self, op: OperationOut) -> list[str]:
        tid = self._target(op, 1)[0]
        d, c = self.tax.locate(tid)
        if c is None:
            raise OperationError(f"{tid} is not a characteristic")
        d.characteristics.remove(c)
        self.tax.dimensions.append(self._dimension(
            DimSpec(name=op.name or c.name, definition=op.definition or c.definition,
                    application_rule=op.application_rule, perspective=op.perspective or d.perspective,
                    characteristics=op.characteristics), [tid]))
        return [tid]

    def _demote(self, op: OperationOut) -> list[str]:
        src, dst = self._target(op, 2)[:2]
        a, b = self._dim(src), self._dim(dst)
        if a is b:
            raise OperationError("a dimension cannot be demoted into itself")
        self.tax.dimensions.remove(a)
        b.characteristics.append(self._char(b.id, CharSpec(name=op.name or a.name, definition=op.definition or
                                                           a.definition), [src]))
        return [src, dst]

    def _delete(self, op: OperationOut) -> list[str]:
        tid = self._target(op, 1)[0]
        d = self.tax.dimension(tid)
        if d is not None:
            self.tax.dimensions.remove(d)
            return [tid]
        d, c = self.tax.locate(tid)
        if c is None:
            raise OperationError(f"{tid} is not an element of the taxonomy")
        d.characteristics.remove(c)
        return [tid]


def apply_operations(tax: Taxonomy, ops: list[OperationOut], inp: InputSpec, cfg: AppConfig, iteration: int,
                     origin: str, check: bool) -> Result:
    """Execute ``ops`` in order on a copy of ``tax``. Returns the new taxonomy, the log of the executed operations,
    the operations skipped because they cannot be executed and, with ``check``, the violations of the invariants."""
    ex = _Executor(tax, inp, iteration, origin)
    res = Result(taxonomy=ex.tax)
    for i, op in enumerate(ops, start=1):
        snapshot = ex.tax.model_copy(deep=True)
        try:
            res.logs.append(ex.run(op))
        except OperationError as exc:
            ex.tax = snapshot
            res.skipped.append(f"operation {i} ({op.op} {op.target or op.name}): {exc}")
    if check:
        res.violations = [f"R5 {p}" for p in invariants(ex.tax, inp, cfg)]
    else:   # ablation: drop what cannot exist
        for d in ex.tax.dimensions:
            d.characteristics = [c for c in d.characteristics if c.name.strip()]
        ex.tax.dimensions = [d for d in ex.tax.dimensions if d.name.strip() and d.characteristics]
    res.taxonomy = ex.tax
    return res
