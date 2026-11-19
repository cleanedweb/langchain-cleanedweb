"""Standard integration tests for the two tools that need no key (find, get).

They call the public, no-key catalog read endpoints and never run an API:
    pytest tests/integration_tests -m live
"""

from __future__ import annotations

from typing import Any, Dict, Type

import pytest
from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_cleanedweb import CleanedWebFindAPI, CleanedWebGetAPI

pytestmark = pytest.mark.live


class TestFindAPIIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[CleanedWebFindAPI]:
        return CleanedWebFindAPI

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        return {"query": "product", "limit": 3}


class TestGetAPIIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[CleanedWebGetAPI]:
        return CleanedWebGetAPI

    @property
    def tool_invoke_params_example(self) -> Dict[str, Any]:
        # The GitHub Topics Repositories API from the public documentation.
        return {"api_id": "generated_047a8ebb25911ccf62f4a212"}
