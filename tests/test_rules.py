from .conftest import ScriptedLLM

from etdp.classify import examine
from etdp.conditions import objective
from etdp.config import AppConfig, InputSpec
from etdp.models import Cell, Characteristic, Dimension, DomainObject, Evidence, IterationRecord, OperationLog, RunState, Taxonomy
from etdp.steps import approach_rule, route



def state(purpose_type="identification_and_structuring", nature="descriptive"):
    inp = InputSpec(observed_phenomenon="p", target_user_groups=["u"], intended_purposes=["x"],
                    purpose_type=purpose_type, purpose_nature=nature, domain_of_objects="d", perspectives=["A"])
    return RunState(run_id="t", input=inp)


def test_r1_first_approach():
    assert approach_rule(state())[0] == "e"
    assert approach_rule(state("structuring"))[0] == "c"
    assert approach_rule(state(nature="normative"))[0] == "c"


def test_r2_and_r3():
    st = state()
    st.iterations.append(IterationRecord(number=1, kind="e"))
    assert approach_rule(st) == ("c", "R2: at least one iteration of each approach (TDR 9)")
    st.iterations.append(IterationRecord(number=2, kind="c"))
    assert approach_rule(st)[0] == "e"                     # alternation
    st.taxonomy = Taxonomy(dimensions=[Dimension(id="D1", name="d", perspective="A", characteristics=[
        Characteristic(id="D1.C1", name="a"), Characteristic(id="D1.C2", name="b")])])
    st.iterations.append(IterationRecord(number=3, kind="e"))
    assert approach_rule(st)[0] == "e" and "R3" in approach_rule(st)[1]   # empty empirical characteristics


def test_r4_review_once_after_the_first_iteration_then_the_llm_chooses_the_reentry(make):
    llm = ScriptedLLM()
    ctx = make(llm=llm).ctx
    st = ctx.state
    st.iterations += [IterationRecord(number=1, kind="r")]      # whatever the type of the first iteration
    route(ctx, "12", ["O3"])
    assert st.next_step == "4" and ctx.record.entry_reason.startswith("R4") and not llm.calls.get("choose_entry")
    st.meta_reviewed = True
    llm.entry = "10"
    route(ctx, "14", ["concise"])
    assert st.next_step == "10" and llm.calls["choose_entry"] == 1 and st.iterations[-1].kind == "r"
    llm.entry = "4"                                              # not an option: the default (new evidence) applies
    route(ctx, "12", ["O3"])
    assert st.next_step == "6"


def make_state():
    st = state()
    st.input.perspectives = ["A"]
    d = Dimension(id="D1", name="Price", perspective="A", characteristics=[
        Characteristic(id="D1.C1", name="Free"), Characteristic(id="D1.C2", name="Paid"),
        Characteristic(id="D1.C3", name="Mixed", origin="conceptual")])
    st.taxonomy = Taxonomy(dimensions=[d])
    sig = d.signature()
    st.objects = {"O1": DomainObject(id="O1", name="a", cells={"D1": Cell(value="D1.C1", key=sig)}),
                  "O2": DomainObject(id="O2", name="b", cells={"D1": Cell(value="D1.C2", key=sig)})}
    st.iterations.append(IterationRecord(number=1, kind="e"))
    return st


def det9(st):
    return objective(st, AppConfig())[1]["O9"]


def test_objective_conditions():
    st = make_state()
    cfg = AppConfig()
    ok, det, issues = objective(st, cfg)
    assert ok["O1"] and ok["O3"] and "exempt" in det["O3"]           # conceptual characteristic exempt (TDR 19)
    assert not ok["O10"] and "O4" not in ok and "O9" not in ok               # perspective A has one dimension; O9 not checked
    st.current.operations = [OperationLog(iteration=1, op="add_characteristic"), OperationLog(iteration=1, op="split")]
    assert objective(st, cfg)[0]["O5"]               # the first e iteration builds the taxonomy
    st.iterations.insert(0, IterationRecord(number=0, kind="e"))                     # now a later e iteration
    st.objects["O2"].cells["D1"].value = "misfit"
    ok, _, issues = objective(st, cfg)
    assert ok["O5"] is False and not ok["O3"] and "O9" not in ok     # an e iteration with an addition
    assert not any(i.startswith("O9") for i in issues) and "1 misfits" in det9(st)   # reported, not checked
    st.current.kind = "c"
    ok, det, _ = objective(st, cfg)
    assert ok["O5"] and "not checked" in det["O5"]                                              # c iteration: no O5
    st.current.kind = "r"
    ok = objective(st, cfg)[0]
    assert ok["O5"]                                                                             # nor a revision
    st.current.kind = "e"
    st.objects["O1"].cells.clear()
    assert not objective(st, cfg)[0]["O1"]


def test_negation_characteristic_needs_no_object():
    st = make_state()
    d = st.taxonomy.dimensions[0]
    d.characteristics[2] = Characteristic(id="D1.C3", name="No price: donations", negation=True)
    sig = d.signature()
    for o in st.objects.values():
        o.cells["D1"].key = sig
    ok, det, _ = objective(st, AppConfig())
    assert ok["O3"] and "D1.C3" in det["O3"]


def test_classification_values_are_checked_against_the_taxonomy(make):
    pipe = make()
    d = Dimension(id="D1", name="Price", perspective="Business", characteristics=[
        Characteristic(id="D1.C1", name="Free"), Characteristic(id="D1.C2", name="Paid")])
    tax = Taxonomy(dimensions=[d])
    o = DomainObject(id="O1", name="Alpha", evidence=[Evidence(doc_id="x", quote="Alpha is free to use for everyone.")])
    answers = iter([{"value": "D1.C1"}, {"value": "D9.C9"}, {"value": "misfit"}, {"value": "no_information"}])
    pipe.ctx.llm.classify_hook = lambda name, dim: next(answers)
    values = []
    for _ in range(4):
        o.cells.clear()
        values.append(examine(pipe.ctx, tax, [o])[0]["O1"]["D1"].value)
    assert values == ["D1.C1", "no_information", "misfit", "no_information"]       # an invalid value is no information


def test_a_change_of_wording_keeps_the_classified_cells():
    from etdp.classify import stale_dimensions
    d = Dimension(id="D1", name="Price", perspective="A", characteristics=[
        Characteristic(id="D1.C1", name="Free"), Characteristic(id="D1.C2", name="Paid")])
    tax = Taxonomy(dimensions=[d])
    o = DomainObject(id="O1", name="a", cells={"D1": Cell(value="D1.C1", key=d.signature(), text=d.wording())})
    n = DomainObject(id="O2", name="b", cells={"D1": Cell(value="no_information", key=d.signature(), text=d.wording())})
    assert not stale_dimensions(o, tax) and not stale_dimensions(n, tax)
    d.definition, d.characteristics[1].name = "How users pay", "Subscription"          # wording only
    assert not stale_dimensions(o, tax) and o.cells["D1"].text == d.wording()           # kept, no request
    assert stale_dimensions(n, tax) == [d]                                              # no characteristic: examined again
    d.characteristics.append(Characteristic(id="D1.C3", name="Mixed"))                  # structure changed
    assert stale_dimensions(o, tax) == [d]


def test_judge_memory_first_assessment():
    from etdp.steps import judge_memory
    from etdp.models import RunState
    st = RunState.model_construct(iterations=[])
    assert "first" in judge_memory(st)
