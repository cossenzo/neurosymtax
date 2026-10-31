"""R4 (the domain bounds the meta-characteristic) and the relevance of the passages."""

from etdp.documents import rank_passages
from etdp.models import Dimension, Characteristic, DomainObject, Evidence, Taxonomy
from etdp.steps import stays_in_domain

from .conftest import ScriptedLLM

CHUNK = "OBJECT Alpha Market: Alpha Market is a digital platform with Free features."


def test_r6_refinement_must_not_move_away_from_the_domain(make):
    ctx = make().ctx
    old = "How digital platforms create and capture value."
    assert stays_in_domain(ctx, old, old)
    assert not stays_in_domain(ctx, old, "How cooking recipes are written and shared by chefs.")

    class LLM(ScriptedLLM):
        def _meta_review(self, v):
            return {"keep": False, "meta_characteristic": "How cooking recipes are written.", "reason": "wider"}
    llm = LLM()
    llm.judge_pass = False                                                  # forces a re-entry, hence the review
    st = make(llm=llm).run()
    review = next(r.meta_review for r in st.iterations if r.meta_review)
    assert review.startswith("refinement rejected by R4") and "cooking" not in st.meta_characteristic


def test_passages_most_relevant_to_the_taxonomy_are_kept(make):
    ctx = make().ctx
    ctx.cfg.documents.passages_per_object = 2
    ctx.state.taxonomy = Taxonomy(dimensions=[Dimension(id="D1", name="Pricing", definition="pricing of the platform",
                                                        perspective="Business", characteristics=[
                                                            Characteristic(id="D1.C1", name="Free"),
                                                            Characteristic(id="D1.C2", name="Paid")])])
    filler = [f"Alpha was mentioned in report number {i} of the year." for i in range(6)]
    relevant = ["Alpha pricing of the platform is free.", "The pricing of the Alpha platform is paid."]
    o = DomainObject(id="O1", name="Alpha", evidence=[Evidence(doc_id="x", quote=q) for q in filler + relevant])
    rank_passages(ctx, o)
    assert sorted(e.quote for e in o.evidence) == sorted(relevant)
