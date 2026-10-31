import pytest

from etdp import goals
from etdp.models import Cell, DomainObject



def test_registry_follows_table_4_of_kundisch():
    assert set(goals.GOALS) == {"describing", "identifying", "classifying", "analyzing", "clustering"}
    assert goals.GOALS["clustering"].users_aim.startswith("cluster objects")
    p = goals.plan([{"goal": "classifying", "targets": {"kappa": 0.7}}, {"goal": "analyzing"}])
    crit = {c["measure"]: c for g in p for c in g["criteria"]}
    assert crit["kappa"]["target"] == 0.7 and crit["misfit_share"]["target"] == 0.30
    assert crit["discriminating_dimensions"]["remedy"] == "10" and crit["misfit_share"]["remedy"] == "6"
    assert goals.unknown_targets([{"goal": "classifying", "targets": {"silhouette": 1}}]) == ["classifying: silhouette"]


def objs(profiles):
    out = []
    for i, p in enumerate(profiles):
        out.append(DomainObject(id=f"O{i}", name=f"o{i}", cells={f"D{j}": Cell(value=v) for j, v in enumerate(p)}))
    return out


def test_measures_and_assessment():
    everything = objs([("a", "x"), ("a", "y"), ("b", "x"), ("b", "y"), ("a", "x"), ("b", "y")])
    new = everything[:2]
    first = {o.id: o.cells for o in new}
    second = {"O0": {"D0": Cell(value="a"), "D1": Cell(value="x")}, "O1": {"D0": Cell(value="b"), "D1": Cell(value="y")}}
    m = goals.measure(new, first, second, everything, ["D0", "D1"], 0.9, 10)
    assert m["kappa_per_dimension"]["D1"] == 1.0 and m["kappa_per_dimension"]["D0"] == 0.0
    assert m["distinct_profiles"] == round(2 / 6, 4) and m["discriminating_dimensions"] == 1.0
    assert m["informed_share"] == 1.0 and m["misfit_share"] == 0 and m["cluster_silhouette"] is not None
    plan = goals.plan([{"goal": "classifying"}, {"goal": "identifying"}])
    res = goals.assess(plan, m, 2)
    unmet = {r["measure"] for r in res if not r["met"]}
    assert unmet == {"kappa", "distinct_profiles"}
    assert not goals.assess(plan, {**m, "new_objects": 1}, 2)[0]["met"]


def test_kappa():
    assert goals.cohen_kappa(["a", "b"], ["a", "b"]) == 1.0 and goals.cohen_kappa(["a", "a"], ["a", "a"]) == 1.0
    assert goals.cohen_kappa(["a", "b", "a", "b"], ["a", "a", "b", "b"]) == 0.0


@pytest.mark.parametrize("goal", ["describing", "identifying", "classifying", "analyzing", "clustering"])
def test_every_goal_runs_end_to_end(make, inp, goal):
    inp2 = type(inp).model_validate({**inp.model_dump(), "evaluation_goals": [goal]})
    st = make(run_input=inp2).run()
    assert st.evaluation_plan[0]["goal"] == goal
    assert st.status in ("completed", "max_iterations_reached")
    assert all("met" in r for r in st.evaluation.get("results", []))


def test_config_targets_override_registry_defaults():
    plan = goals.plan([{"goal": "classifying"}], {"misfit_share": 0.4})
    crit = {c["measure"]: c["target"] for c in plan[0]["criteria"]}
    assert crit["misfit_share"] == 0.4 and crit["kappa"] == 0.61
