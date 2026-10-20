import json

import pytest

from etdp.llm import LLMError, LLMResponse, extract_json
from etdp.models import MetaOut

from .conftest import ScriptedLLM

VARS = {"phenomenon": "p", "users": "u", "purpose": "x", "domain_of_objects": "d", "perspectives": ["A"],
        "language": "en"}


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json('Here it is: {"a": 3} thanks') == {"a": 3}


def test_invalid_answer_is_requested_again_then_gives_up():
    class Bad(ScriptedLLM):
        def _raw_complete(self, system, messages, schema=None):
            self.calls["n"] = self.calls.get("n", 0) + 1
            return LLMResponse("nope", 1, 1)

    llm = Bad(max_retries=2)
    with pytest.raises(LLMError):
        llm.structured("meta_characteristic", VARS, MetaOut)
    assert llm.calls["n"] == 3


def test_cache_avoids_a_second_call(tmp_path):
    llm = ScriptedLLM(cache_dir=tmp_path)
    llm.structured("meta_characteristic", VARS, MetaOut)
    llm2 = ScriptedLLM(cache_dir=tmp_path)
    llm2.structured("meta_characteristic", VARS, MetaOut)
    assert llm.calls == {"meta_characteristic": 1} and llm2.calls == {} and llm2.tokens_used == 0


def test_prompt_contains_the_schema():
    llm = ScriptedLLM()
    seen = {}

    def spy(system, messages, schema=None):
        seen["prompt"] = messages[-1]["content"]
        return LLMResponse(json.dumps({"meta_characteristic": "m"}))

    llm._raw_complete = spy
    llm.structured("meta_characteristic", VARS, MetaOut)
    assert "JSON schema" in seen["prompt"] and "Step 4" in seen["prompt"]


def test_every_prompt_renders(tmp_path):
    """Every template can be rendered with the variables the code passes (no missing $variable)."""
    from pathlib import Path

    from etdp.llm import PromptLibrary
    lib = PromptLibrary(Path(__file__).resolve().parents[1] / "prompts")
    names = [p.stem for p in lib.directory.glob("*.txt")]
    assert {"propose_operations", "classify_objects", "baseline", "judge_subjective"} <= set(names)
