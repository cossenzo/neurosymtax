from pathlib import Path

import pytest
from pydantic import ValidationError

from etdp.config import AppConfig, InputSpec, load_config, load_input
from etdp.documents import fit_query
from etdp.names import is_generic, same_object
from etdp.sources.fulltext import html_to_text

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_files_and_ablation_differences():
    a, b = load_config(ROOT / "config.yaml"), load_config(ROOT / "config_ablation.yaml")
    da, db = a.model_dump(), b.model_dump()
    diff = {f"{s}.{k}" for s in da for k in da[s] if da[s][k] != db[s][k]}
    assert diff == {"method.symbolic_approach", "method.verify_operations"}
    assert a.limits.max_iterations == 15 and a.scholarly.results == 3 and a.web.results == 3
    load_input(ROOT / "input_defi.yaml")
    load_input(ROOT / "input.example.yaml")


def test_input_validation():
    with pytest.raises(ValidationError):
        InputSpec(observed_phenomenon="p", target_user_groups=[], intended_purposes=["x"],
                  purpose_type="structuring", domain_of_objects="d")
    with pytest.raises(ValidationError):
        AppConfig.model_validate({"method": {"unknown": 1}})
    i = InputSpec(observed_phenomenon="p", target_user_groups=["a", "b"], intended_purposes=["x"],
                  purpose_type="structuring", domain_of_objects="d")
    assert i.perspective_names == ["Perspective"] and i.users == "a; b"


def test_query_fitting():
    assert fit_query("one two three four five six seven eight nine", 3, 8) == "one two three four five six seven eight"
    assert fit_query("alpha", 3, 8, ["beta gamma", "delta"]) == "alpha beta gamma"


def test_names_and_html():
    assert same_object(["Uniswap V3"], ["Uniswap"]) and same_object(["DeFi Money Market (DMM)"], ["DMM"])
    assert is_generic("DeFi protocol") and not is_generic("Aave")
    assert html_to_text("<html><script>x</script><p>Hello</p><p>World</p></html>") == "Hello\n\nWorld"


def test_tavily_request(monkeypatch):
    from etdp.config import WebConfig
    from etdp.sources import web

    sent = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"url": "https://docs.example/x", "title": "X docs", "raw_content": "X is a protocol."}]}

    def post(url, json, timeout, headers):
        sent.update(url=url, body=json, headers=headers)
        return Resp()

    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setattr(web.requests, "post", post)
    pages = web.TavilySearch(WebConfig(), 1000).search("defi protocols", 10)
    assert pages[0].text == "X is a protocol." and sent["body"]["max_results"] == 10
    assert sent["headers"]["Authorization"] == "Bearer k"
