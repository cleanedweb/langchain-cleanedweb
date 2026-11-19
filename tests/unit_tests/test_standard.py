"""LangChain's standard unit tests for each tool."""

from __future__ import annotations

from typing import Any, Dict, Tuple, Type

from langchain_tests.unit_tests import ToolsUnitTests

from langchain_cleanedweb import CleanedWebFindAPI, CleanedWebGetAPI, CleanedWebRunAPI


class _Env:
    @property
    def init_from_env_params(self) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        return {"CLEANEDWEB_API_KEY": "key-from-env"}, {}, {"api_key": "key-from-env"}


class TestFindAPIUnit(_Env, ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[CleanedWebFindAPI]:
        return CleanedWebFindAPI

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"site": "github.com", "fields": ["title"]}


class TestGetAPIUnit(_Env, ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[CleanedWebGetAPI]:
        return CleanedWebGetAPI

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"api_id": "generated_047a8ebb25911ccf62f4a212"}


class TestRunAPIUnit(_Env, ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[CleanedWebRunAPI]:
        return CleanedWebRunAPI

    @property
    def tool_constructor_params(self) -> Dict[str, Any]:
        return {"api_key": "test-key"}

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"api_id": "a", "endpoint_id": "e", "input": {}, "max_items": 5}
