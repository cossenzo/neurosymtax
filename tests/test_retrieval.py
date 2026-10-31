"""Documents are read in full; searches for objects look for other objects, not for characteristics."""

from etdp.documents import read_chunks, register_objects
from etdp.models import ObjectOut
from etdp.steps import SEARCH_AIMS

from .conftest import ScriptedLLM


def test_every_chunk_of_a_document_is_read(make):
    ctx = make().ctx
    ctx.cfg.documents.chunk_size_tokens, ctx.cfg.documents.chunk_overlap_tokens = 40, 4
    lines = [f"Sentence number {i} names the object Omega {i} of the domain." for i in range(60)]
    ctx.store.save("long", [(1, " ".join(lines))])
    chunks = read_chunks(ctx, ["long"])
    assert len(chunks) > 4 and all(doc == "long" for doc, _ in chunks)
    text = " ".join(c for _, c in chunks)
    assert "Omega 0 " in text and "Omega 59 " in text                     # first and last sentence


def test_object_searches_name_registered_objects_and_ignore_open_issues(make):
    llm = ScriptedLLM()
    st = make(llm=llm).run()
    requests = llm.requests["formulate_query"]
    objects = [v for v in requests if v["aim"] == SEARCH_AIMS["objects"]]
    concepts = [v for v in requests if v["aim"] == SEARCH_AIMS["concepts"]]
    assert objects and concepts
    assert all("Objects already registered" in v["focus"] and "Open issues" not in v["focus"] for v in objects)
    assert any("Alpha Market" in v["focus"] for v in objects[1:] + [v for v in requests
                                                                    if v["aim"] == SEARCH_AIMS["evaluation"]])
    assert all("Open issues" in v["focus"] for v in concepts)
    assert st.queries and all(2 <= len(q.split()) <= 5 for q in st.queries)          # few, broad keywords


def test_new_objects_are_described_by_the_llm_in_groups(make):
    llm = ScriptedLLM()
    ctx = make(llm=llm).ctx
    ctx.cfg.documents.objects_per_description = 2
    ctx.store.save("doc", [(1, "Alpha Market, Beta Hub and Gamma Pay are digital platforms.")])
    found = [ObjectOut(name=n) for n in ("Alpha Market", "Beta Hub", "Gamma Pay")]
    ids = register_objects(ctx, found, ["doc"], 1)
    assert len(ids) == 3 and llm.calls["describe_objects"] == 2                 # 3 objects, groups of 2
    asked = llm.requests["describe_objects"]
    assert asked[0]["objects"] == "'Alpha Market', 'Beta Hub'" and asked[1]["objects"] == "'Gamma Pay'"
    llm_docs = [d for d in ctx.state.documents.values() if d.source == "llm"]
    assert len(llm_docs) == 2
    alpha = ctx.state.objects[ids[0]]
    assert any(e.doc_id.startswith("llm:") and "Alpha Market is a digital platform" in e.quote for e in alpha.evidence)


def test_only_the_search_string_is_relaxed_never_the_year_range(make, inp):
    from etdp.documents import _scholarly
    from etdp.sources.http import SearchProvider

    class Recorder(SearchProvider):
        name = "recorder"

        def __init__(self):
            self.calls = []

        def search(self, query, limit, year_range=None):
            self.calls.append((query, year_range))
            return []

    inp = inp.model_copy(update={"year_range": (2008, 2023)})
    pipe = make(run_input=inp)
    rec = Recorder()
    pipe.ctx.scholarly = rec
    _scholarly(pipe.ctx, "DeFi taxonomy typology governance classification", 3, 1)
    queries = [q for q, _ in rec.calls]
    assert len(queries) == 3 and queries[0].count(" ") == 4 and queries[-1].count(" ") == 1   # 5, 4 and 2 words
    assert all(years == (2008, 2023) for _, years in rec.calls)                              # the years never change
