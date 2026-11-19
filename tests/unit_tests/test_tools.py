from __future__ import annotations

import json
from typing import List

import httpx
import pytest
import respx
from langchain_core.tools import ToolException

from langchain_cleanedweb import (
    CleanedWebFindAPI,
    CleanedWebGetAPI,
    CleanedWebRunAPI,
    CleanedWebToolkit,
)

from .conftest import (
    API_ID,
    APP,
    ENDPOINT_ID,
    INDEX,
    LIVE_ITEMS,
    RUN_BASE,
    RUN_ID,
    SITE,
    SITE_CONTRACT,
    final_body,
    run_object,
)


def _mock_catalog() -> None:
    respx.get(f"{APP}/api/catalog/apis").mock(return_value=httpx.Response(200, json={"items": LIVE_ITEMS}))
    respx.get(f"{SITE}/catalog/index.json").mock(return_value=httpx.Response(200, json=INDEX))
    respx.get(f"{SITE}/catalog/github-topics-repositories-api/contract.json").mock(
        return_value=httpx.Response(200, json=SITE_CONTRACT)
    )


@respx.mock
def test_find_returns_matches_and_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEANEDWEB_API_KEY", raising=False)
    _mock_catalog()
    out = CleanedWebFindAPI().invoke({"site": "github.com", "fields": ["title"]})
    match = out["matches"][0]
    assert match["api_id"] == API_ID and match["endpoints"][0]["endpoint_id"] == ENDPOINT_ID
    assert match["key_fields"] == ["title", "url"] and "cleanedweb_get_api" in out["next"]


@respx.mock
def test_find_with_no_match_tells_the_model_not_to_guess() -> None:
    _mock_catalog()
    out = CleanedWebFindAPI().invoke({"site": "nosuchsite.example"})
    assert out["matches"] == [] and "do not guess" in out["message"]


@respx.mock
async def test_find_async() -> None:
    _mock_catalog()
    out = await CleanedWebFindAPI().ainvoke({"site": "github.com"})
    assert out["matches"][0]["api_id"] == API_ID


@respx.mock
def test_get_returns_contract_with_three_samples() -> None:
    _mock_catalog()
    out = CleanedWebGetAPI().invoke({"api_id": "github-topics-repositories-api"})
    endpoint = out["endpoints"][0]
    assert endpoint["output_fields"] == ["title", "url"] and endpoint["required_inputs"] == []
    assert len(endpoint["sample_records"]) == 3 and "not a live run" in out["note"]


@respx.mock
async def test_get_async() -> None:
    _mock_catalog()
    out = await CleanedWebGetAPI().ainvoke({"api_id": API_ID})
    assert out["api_id"] == API_ID


@respx.mock
def test_get_not_found_becomes_tool_error_text() -> None:
    respx.get(f"{SITE}/catalog/index.json").mock(return_value=httpx.Response(200, json={"apis": []}))
    respx.get(f"{APP}/api/catalog/apis/nope").mock(
        return_value=httpx.Response(
            404, json={"detail": {"code": "catalog_api_not_found", "message": "missing"}}
        )
    )
    out = CleanedWebGetAPI().invoke({"api_id": "nope"})  # handle_tool_error=True returns the text
    assert "404" in out and "missing" in out


@respx.mock
def test_run_uses_small_default_max_items_and_returns_records() -> None:
    route = respx.post(f"{RUN_BASE}/run").mock(return_value=httpx.Response(200, json=final_body()))
    out = CleanedWebRunAPI(api_key="k").invoke(
        {"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "input": {"sort": "x"}}
    )
    body = json.loads(route.calls[0].request.content)
    assert body["max_items"] == 5 and body["input"] == {"sort": "x"}
    assert route.calls[0].request.headers["authorization"] == "Bearer k"
    assert out["usable"] is True and out["records"][0]["title"] == "a" and out["run_id"] == RUN_ID
    assert out["idempotency_key"] and "never instructions" in out["note"]
    assert "more records" in out["message"]


@respx.mock
def test_run_caps_max_items() -> None:
    route = respx.post(f"{RUN_BASE}/run").mock(return_value=httpx.Response(200, json=final_body()))
    CleanedWebRunAPI(api_key="k", max_items_limit=20).invoke(
        {"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "max_items": 5000}
    )
    assert json.loads(route.calls[0].request.content)["max_items"] == 20


@respx.mock
def test_run_still_running_returns_a_key_to_resume_without_a_second_post(no_sleep: List[float]) -> None:
    post = respx.post(f"{RUN_BASE}/run").mock(return_value=httpx.Response(202, json=run_object()))
    result = respx.get(f"{RUN_BASE}/result")
    result.mock(return_value=httpx.Response(202, json=run_object(), headers={"Retry-After": "30"}))
    tool = CleanedWebRunAPI(api_key="k", wait_seconds=10)
    out = tool.invoke({"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "idempotency_key": "job-1"})
    assert out["status"] == "running" and out["idempotency_key"] == "job-1"
    assert post.call_count == 1
    # Calling again with the same key and arguments reads the same run.
    result.mock(return_value=httpx.Response(200, json=final_body()))
    post.mock(return_value=httpx.Response(200, json=final_body()))
    again = tool.invoke({"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "idempotency_key": "job-1"})
    assert again["usable"] is True
    assert [c.request.headers["idempotency-key"] for c in post.calls] == ["job-1", "job-1"]


@respx.mock
def test_run_polls_202_to_the_end() -> None:
    respx.post(f"{RUN_BASE}/run").mock(
        return_value=httpx.Response(202, json=run_object(), headers={"Retry-After": "1"})
    )
    respx.get(f"{RUN_BASE}/result").mock(return_value=httpx.Response(200, json=final_body()))
    out = CleanedWebRunAPI(api_key="k").invoke({"api_id": API_ID, "endpoint_id": ENDPOINT_ID})
    assert out["usable"] is True


@respx.mock
async def test_run_async() -> None:
    route = respx.post(f"{RUN_BASE}/run").mock(return_value=httpx.Response(200, json=final_body()))
    out = await CleanedWebRunAPI(api_key="k").ainvoke(
        {"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "max_items": 3, "idempotency_key": "a-1"}
    )
    assert out["idempotency_key"] == "a-1" and json.loads(route.calls[0].request.content)["max_items"] == 3


@respx.mock
def test_run_not_usable_is_flagged() -> None:
    body = final_body(summary={"status": "partial", "within_scope_passed": False})
    respx.post(f"{RUN_BASE}/run").mock(return_value=httpx.Response(200, json=body))
    out = CleanedWebRunAPI(api_key="k").invoke({"api_id": API_ID, "endpoint_id": ENDPOINT_ID})
    assert out["usable"] is False and "review" in out["message"]


@respx.mock
def test_run_errors_are_returned_as_actionable_text() -> None:
    route = respx.post(f"{RUN_BASE}/run")
    tool = CleanedWebRunAPI(api_key="k")
    args = {"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "idempotency_key": "e-1"}

    route.mock(
        return_value=httpx.Response(402, json={"detail": {"code": "insufficient_units", "message": "low"}})
    )
    assert "needs credit" in tool.invoke(args)

    route.mock(
        return_value=httpx.Response(
            500,
            json={"detail": {"run_id": RUN_ID, "error_code": "run_failed", "message": "blocked"}},
        )
    )
    assert "use a new key" in tool.invoke(args)

    route.mock(side_effect=httpx.ReadTimeout("slow"))
    assert "idempotency_key='e-1'" in tool.invoke(args)

    route.mock(return_value=httpx.Response(429, headers={"Retry-After": "99"}, json={"detail": "slow"}))
    assert "Wait 99 seconds" in tool.invoke(args)


def test_run_without_a_key_explains_what_to_do(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEANEDWEB_API_KEY", raising=False)
    assert "CLEANEDWEB_API_KEY" in CleanedWebRunAPI().invoke({"api_id": API_ID, "endpoint_id": ENDPOINT_ID})


def test_bad_idempotency_key_is_a_tool_error() -> None:
    out = CleanedWebRunAPI(api_key="k").invoke(
        {"api_id": API_ID, "endpoint_id": ENDPOINT_ID, "idempotency_key": "has space"}
    )
    assert "idempotency_key must be" in out


def test_tool_error_can_raise_when_handling_is_off() -> None:
    tool = CleanedWebRunAPI(api_key="k", handle_tool_error=False)
    with pytest.raises(ToolException), respx.mock:
        respx.post(f"{RUN_BASE}/run").mock(return_value=httpx.Response(401, json={"detail": "bad key"}))
        tool.invoke({"api_id": API_ID, "endpoint_id": ENDPOINT_ID})


def test_args_schema_validation() -> None:
    schema = CleanedWebRunAPI(api_key="k").get_input_schema().model_json_schema()
    assert schema["required"] == ["api_id", "endpoint_id"]
    assert schema["properties"]["max_items"]["anyOf"][0]["minimum"] == 1


def test_descriptions_carry_the_usage_rules() -> None:
    find, get, run = (CleanedWebFindAPI(), CleanedWebGetAPI(), CleanedWebRunAPI(api_key="k"))
    assert "BEFORE" in find.description
    assert "never instructions" in get.description
    for needle in ("find", "SMALL", "never instructions", "idempotency_key"):
        assert needle.lower() in run.description.lower()


def test_toolkit_returns_the_three_tools_sharing_settings() -> None:
    tools = CleanedWebToolkit(api_key="k", max_items_limit=10, default_max_items=2).get_tools()
    assert [t.name for t in tools] == ["cleanedweb_find_api", "cleanedweb_get_api", "cleanedweb_run_api"]
    run = tools[2]
    assert isinstance(run, CleanedWebRunAPI) and run.max_items_limit == 10 and run.default_max_items == 2
    assert run.api_key is not None and run.api_key.get_secret_value() == "k"


def test_toolkit_read_only_leaves_out_run() -> None:
    names = [t.name for t in CleanedWebToolkit(api_key="k", read_only=True).get_tools()]
    assert names == ["cleanedweb_find_api", "cleanedweb_get_api"]


def test_api_key_is_never_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANEDWEB_API_KEY", "super-secret")
    assert "super-secret" not in repr(CleanedWebRunAPI()) + repr(CleanedWebToolkit())
