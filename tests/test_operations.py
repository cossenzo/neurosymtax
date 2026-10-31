import pytest

from etdp.config import AppConfig, InputSpec
from etdp.models import OperationOut, Taxonomy
from etdp.operations import apply_operations, invariants

INP = InputSpec(observed_phenomenon="p", target_user_groups=["u"], intended_purposes=["x"],
                purpose_type="structuring", domain_of_objects="d", perspectives=["A", "B"])
CFG = AppConfig()


def run(ops, tax=None, check=True):
    return apply_operations(tax or Taxonomy(), [OperationOut(**o) for o in ops], INP, CFG, 1, "empirical", check)


def dim(name, persp="A", chars=("x", "y"), ev=("O1",)):
    return {"op": "add_dimension", "name": name, "perspective": persp, "evidence": list(ev),
            "characteristics": [{"name": f"{name}-{c}"} for c in chars]}


@pytest.fixture
def base():
    return run([dim("Price"), dim("Sides"), dim("Gov", "B")]).taxonomy


def test_add_dimension_assigns_permanent_ids_and_logs():
    res = run([dim("Price")])
    d = res.taxonomy.dimensions[0]
    assert d.id == "D1" and [c.id for c in d.characteristics] == ["D1.C1", "D1.C2"] and not res.violations
    assert res.logs[0].created == ["D1", "D1.C1", "D1.C2"] and res.logs[0].evidence == ["O1"]


def test_evidence_is_not_checked():
    res = run([dim("Price", ev=()), dim("Sides", ev=("O9",))])
    assert not res.violations and len(res.taxonomy.dimensions) == 2


def test_a_perspective_outside_the_input_breaks_the_invariants():
    assert "perspective" in run([dim("Price", "Z")]).violations[0]


def test_invariants():
    tax = run([dim("Price", chars=("x",))], check=False).taxonomy
    assert any("at least 2" in p for p in invariants(tax, INP, CFG))
    res = run([dim("Price"), dim("price")])
    assert any("same name" in v for v in res.violations)
    res = run([{**dim("Neg"), "characteristics": [{"name": "a", "negation": True}, {"name": "b", "negation": True}]}])
    assert any("negation" in v for v in res.violations)
    res = run([dim("P1", chars=("same", "a")), {**dim("P2"), "characteristics": [{"name": "P1-same"}, {"name": "b"}]}])
    assert any("unique in the taxonomy" in v for v in res.violations)


def test_rename_swap_delete(base):
    res = run([{"op": "rename", "target": ["D1"], "name": "Pricing", "evidence": ["I1"]},
               {"op": "swap", "target": ["D1", "D2"], "evidence": ["I1"]},
               {"op": "delete", "target": ["D3.C2"], "reason": "no object", "evidence": ["I1"]},
               {"op": "add_characteristic", "target": ["D3"], "name": "Gov-z", "evidence": ["O2"]}], base)
    names = [d.name for d in res.taxonomy.dimensions]
    assert names[:2] == ["Sides", "Pricing"] and not res.violations
    assert [c.id for c in res.taxonomy.dimension("D3").characteristics] == ["D3.C1", "D3.C3"]


def test_negation_characteristics(base):
    res = run([{"op": "add_characteristic", "target": ["D1"], "name": "Free of charge: no fee", "negation": True,
                "evidence": ["O1"]}], base)
    assert not res.violations
    res = run([{"op": "add_characteristic", "target": ["D2"], "name": "No market sides stated", "negation": True,
                "evidence": ["O1"]}], base)
    assert any("missing information" in v for v in res.violations)


def test_split_and_merge(base):
    res = run([{"op": "split", "target": ["D1"], "evidence": ["O1"], "parts": [
        {"name": "Fee level", "perspective": "A", "characteristics": [{"name": "low"}, {"name": "high"}]},
        {"name": "Fee base", "perspective": "A", "characteristics": [{"name": "flat"}, {"name": "rate"}]}]}], base)
    ids = [d.id for d in res.taxonomy.dimensions]
    assert ids == ["D4", "D5", "D2", "D3"] and res.taxonomy.dimension("D4").derived_from == ["D1"]
    res = run([{"op": "merge", "target": ["D1.C1", "D1.C2"], "name": "Price-any", "evidence": ["O1"]},
               {"op": "add_characteristic", "target": ["D1"], "name": "Price-none", "negation": True,
                "evidence": ["O1"]}], base)
    assert [c.name for c in res.taxonomy.dimension("D1").characteristics] == ["Price-any", "Price-none"]
    assert res.logs[0].removed == ["D1.C1", "D1.C2"] and not res.violations


def test_promote_and_demote(base):
    res = run([{"op": "promote", "target": ["D1.C1"], "name": "Freeness", "perspective": "B", "evidence": ["O1"],
                "characteristics": [{"name": "fully"}, {"name": "partly"}]},
               {"op": "add_characteristic", "target": ["D1"], "name": "Price-w", "evidence": ["O1"]},
               {"op": "demote", "target": ["D2", "D3"], "name": "Sided", "evidence": ["O1"]}], base)
    assert not res.violations, res.violations
    assert res.taxonomy.dimension("D2") is None and "Sided" in [c.name for c in res.taxonomy.dimension("D3").characteristics]
    assert res.taxonomy.dimensions[-1].name == "Freeness" and res.taxonomy.dimensions[-1].derived_from == ["D1.C1"]


def test_failed_operation_is_rolled_back_and_others_kept(base):
    res = run([{"op": "rename", "target": ["D9"], "name": "x", "evidence": ["I1"]},
               {"op": "rename", "target": ["D1"], "name": "Cost", "evidence": ["I1"]}], base)
    assert not res.violations and len(res.skipped) == 1 and "D9" in res.skipped[0]   # skipped, not corrected
    assert res.taxonomy.dimension("D1").name == "Cost"


def test_unchecked_operations_in_the_ablation():
    res = run([dim("Price", "Z", ev=()), {"op": "delete", "target": ["D7"]}], check=False)
    assert not res.violations and res.taxonomy.dimensions[0].perspective == "Z"
