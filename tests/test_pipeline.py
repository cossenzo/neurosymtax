import json
import re

import pytest

from .conftest import ScriptedLLM


def test_full_run_completes_and_reports(make):
    pipe = make()
    st = pipe.run()
    assert st.status == "completed", st.message
    kinds = [r.kind for r in st.iterations]
    assert kinds[0] == "e" and "c" in kinds                     # R1, R2
    assert {d.name for d in st.taxonomy.dimensions} == {"Pricing", "Market sides", "Governance", "Hosting"}
    last = st.iterations[-1]
    assert all(last.objective.values()) and all(v["passed"] for v in last.subjective.values())
    assert st.evaluation["kappa"] == 1.0 and st.evaluation["new_objects"] >= 2
    assert all(r["met"] for r in st.evaluation["results"])
    for f in ("taxonomy.json", "taxonomy.md", "operations.json", "iterations.json", "audit.json", "objects_matrix.csv",
              "sources.json", "objects.json"):
        assert (pipe.run_dir / f).exists()
    tax = json.loads((pipe.run_dir / "taxonomy.json").read_text())
    assert tax["perspectives"]["Business"] and tax["perspectives"]["Technology"]
    audit = json.loads((pipe.run_dir / "audit.json").read_text())
    first = audit["iterations"][0]
    assert first["exit"] == "12" and first["objective_unmet"] == [] and first["entry"] == "4"   # required, not failed
    assert audit["iterations"][1]["kind"] == "c" and audit["iterations"][0]["meta_review"]


def test_ablation_run(make, cfg):
    cfg.method.symbolic_approach = cfg.method.verify_operations = False
    llm = ScriptedLLM()
    st = make(llm=llm, config=cfg).run()
    assert st.status in ("completed", "max_iterations_reached")
    assert llm.calls["choose_approach"] >= 1
    assert all(r.kind == "e" for r in st.iterations if r.kind != "r")


def test_rejected_proposal_after_r_corrections_leaves_taxonomy_unchanged(make, cfg):
    llm = ScriptedLLM()
    bad = {"op": "add_dimension", "name": "Pricing", "perspective": "Nowhere", "evidence": ["O1"],
           "characteristics": [{"name": "Free"}, {"name": "Paid"}]}
    llm.propose_hook = lambda stage, v, attempt: [bad]
    pipe = make(llm=llm)
    from etdp.steps import STEPS
    for s in ("1-3", "4", "5", "6", "7e", "8e", "9e"):
        STEPS[s](pipe.ctx)
    rec = pipe.state.current
    assert len(rec.attempts) == cfg.method.r + 1 and all(rec.attempts) and rec.rejected
    assert "violations" in llm.requests["propose_operations"][-1] and llm.requests["propose_operations"][-1]["violations"] != "none"
    STEPS["10"](pipe.ctx)
    assert pipe.state.taxonomy.dimensions == []


def test_a_correction_is_accepted_on_the_second_attempt(make):
    llm = ScriptedLLM()

    def hook(stage, v, attempt):
        if stage == "e" and attempt == 1:
            return [{"op": "add_dimension", "name": "Pricing", "perspective": "Business",
                     "characteristics": [{"name": "Free"}]}]          # no evidence, one characteristic
        return None
    llm.propose_hook = hook
    pipe = make(llm=llm)
    st = pipe.run()
    first = st.iterations[0]
    assert len(first.attempts) == 2 and first.attempts[0] and not first.attempts[1]
    assert st.status == "completed"


def test_revision_iteration_after_a_repairable_failure(make):
    llm = ScriptedLLM()
    llm.judge_pass = False                                              # subjective conditions unmet
    llm.entry = {"14": "10"}                                            # the LLM chooses to revise after Step 14

    def hook(stage, v, attempt):
        if stage == "r":
            llm.judge_pass = True
            issue = v["issues"][0].split(":")[0]
            return [{"op": "rename", "target": ["D1"], "application_rule": "choose the price model stated first",
                     "evidence": [issue], "reason": "judge suggestion"}]
        return None
    llm.propose_hook = hook
    st = make(llm=llm).run()
    kinds = [r.kind for r in st.iterations]
    assert "r" in kinds
    r = next(r for r in st.iterations if r.kind == "r")
    assert r.reason.startswith("chosen by the LLM") and [o.op for o in r.operations] == ["rename"]
    assert re.fullmatch(r"I\d+\.\d+", r.operations[0].evidence[0])          # stable issue id
    assert st.status == "completed"


def test_meta_characteristic_reviewed_once_after_the_first_iteration(make):
    llm = ScriptedLLM()
    llm.judge_pass = False
    st = make(llm=llm).run()
    assert llm.calls.get("meta_review") == 1 and st.meta_reviewed
    assert st.status == "max_iterations_reached" and len(st.iterations) == 8
    assert st.iterations[0].entry == "4" and sum(r.entry == "4" for r in st.iterations) == 1


def test_resume_after_a_crash(make, cfg):
    from etdp.pipeline import Pipeline
    from .conftest import FakeFetcher, FakeScholarly, FakeWeb
    from etdp.embeddings import HashingEmbedder
    pipe = make(llm=ScriptedLLM(fail_on="extract_concepts"))
    with pytest.raises(RuntimeError):
        pipe.run()
    assert pipe.state.status == "failed"
    again = Pipeline.resume(pipe.state.run_id, cfg.output.dir, cfg, llm=ScriptedLLM(), embedder=HashingEmbedder(),
                            scholarly=FakeScholarly(), fetcher=FakeFetcher(), web=FakeWeb())
    assert again.run().status == "completed"


def test_baseline(cfg, inp, tmp_path):
    from etdp.baseline import run_baseline
    run_dir = run_baseline(cfg, inp, str(tmp_path / "out"), "b1", llm=ScriptedLLM())
    doc = json.loads((run_dir / "taxonomy.json").read_text())
    assert len(doc["dimensions"]) == 4 and doc["structure_problems"] == []


def test_violations_and_unmet_subjective_conditions_are_shown(make):
    import logging
    llm = ScriptedLLM()
    llm.judge_pass = False
    llm.entry = {"14": "10"}

    def hook(stage, v, attempt):
        if stage == "r":
            llm.judge_pass = True
            issue = v["issues"][0].split(":")[0]
            if attempt == 1:                                   # a dimension with one characteristic breaks R5
                return [{"op": "add_dimension", "name": "Solo", "perspective": "Business",
                         "characteristics": [{"name": "Only"}], "evidence": [issue]}]
            return [{"op": "rename", "target": ["D1"], "definition": "x", "evidence": [issue]}]
        return None
    llm.propose_hook = hook
    lines: list[str] = []

    class Keep(logging.Handler):
        def emit(self, record):
            lines.append(record.getMessage())
    handler, logger = Keep(level=logging.INFO), logging.getLogger("etdp")
    logger.addHandler(handler)
    try:
        make(llm=llm).run()
    finally:
        logger.removeHandler(handler)
    text = "\n".join(lines)
    assert "subjective conditions met:" in text and "unmet: ['concise'" in text and "  suggestion subjective" in text
    assert "R5: the resulting taxonomy must keep its invariants" in text and "R5 dimension D" in text
    assert "correction: the violations are returned to the LLM" in text


def test_an_operation_that_cannot_be_executed_is_skipped_without_a_correction(make):
    import logging
    llm = ScriptedLLM()
    llm.judge_pass = False
    llm.entry = {"14": "10"}
    llm.propose_hook = lambda stage, v, attempt: ([{"op": "rename", "target": ["D99"], "name": "x"}]
                                                  if stage == "r" else None)
    lines: list[str] = []

    class Keep(logging.Handler):
        def emit(self, record):
            lines.append(record.getMessage())
    handler, logger = Keep(level=logging.INFO), logging.getLogger("etdp")
    logger.addHandler(handler)
    try:
        st = make(llm=llm).run()
    finally:
        logger.removeHandler(handler)
    text = "\n".join(lines)
    assert "skipped: operation 1 (rename ['D99'])" in text and "correction:" not in text
    assert all(len(r.attempts) == 1 for r in st.iterations if r.kind == "r")


def test_a_truncated_answer_is_asked_again_shortly_and_then_rejected(make, cfg):
    from etdp.llm.base import LLMTruncated
    from etdp.steps import STEPS
    llm = ScriptedLLM()
    real = llm.structured
    state = {"cut": 1}

    def structured(task, variables, model):
        if task == "propose_operations" and state["cut"] > 0:
            state["cut"] -= 1
            raise LLMTruncated("cut")
        return real(task, variables, model)
    llm.structured = structured
    pipe = make(llm=llm)
    for s in ("1-3", "4", "5", "6", "7e", "8e", "9e"):
        STEPS[s](pipe.ctx)
    rec = pipe.state.current
    assert len(rec.attempts) == 2 and not rec.rejected and pipe.state.work.proposal is not None   # short answer accepted
    state["cut"] = 99                                                    # every answer is cut: the proposal is rejected
    pipe2 = make(llm=llm)
    for s in ("1-3", "4", "5", "6", "7e", "8e", "9e"):
        STEPS[s](pipe2.ctx)
    assert pipe2.state.current.rejected and pipe2.state.status != "failed"


def test_a_revision_does_not_keep_characteristics_without_objects(make):
    llm = ScriptedLLM()
    llm.judge_pass = False
    llm.entry = {"14": "10"}

    def hook(stage, v, attempt):
        if stage == "r":
            llm.judge_pass = True
            issue = v["issues"][0].split(":")[0]
            return [{"op": "add_dimension", "name": "Support", "perspective": "Business", "evidence": [issue],
                     "characteristics": [{"name": "Chat-only"}, {"name": "Phone-only"}]},       # no object has them
                    {"op": "add_characteristic", "target": ["D1"], "name": "Barter-only", "evidence": [issue]}]
        return None
    llm.propose_hook = hook
    st = make(llm=llm).run()
    r = next(r for r in st.iterations if r.kind == "r")
    names = {c.name for d in st.taxonomy.dimensions for c in d.characteristics}
    assert "Barter-only" not in names and "Support" not in {d.name for d in st.taxonomy.dimensions}
    assert r.operations[-1].op == "delete" and "no classified object" in r.operations[-1].reason
    assert r.objective["O3"]                                          # the revision did not leave O3 unmet


def test_a_passage_without_a_usable_answer_is_skipped_not_fatal(make):
    from etdp.steps import STEPS
    llm = ScriptedLLM()
    real = llm._raw_complete

    def raw(system, messages, schema=None):
        if llm.current_task == "extract_objects" and "Alpha Market" in llm.current_variables.get("text", ""):
            llm.calls["extract_objects"] = llm.calls.get("extract_objects", 0) + 1
            from etdp.llm.base import LLMResponse
            return LLMResponse("", 10, 0, stop_reason="refusal")            # an empty reply
        return real(system, messages, schema)
    llm._raw_complete = raw
    pipe = make(llm=llm)
    for s in ("1-3", "4", "5", "6", "7e"):
        STEPS[s](pipe.ctx)
    names = {o.name for o in pipe.state.objects.values()}
    assert "Alpha Market" not in names and "Gamma Exchange" in names        # only the unreadable passage was lost
