"""LangChain tools for the CleanedWeb catalog: find an API, read its contract, run it."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from cleanedweb import CleanedWebError
from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import ToolException
from pydantic import BaseModel, Field

from ._base import CleanedWebBaseTool, tool_error
from ._descriptions import FIND_DESCRIPTION, GET_DESCRIPTION, RUN_DESCRIPTION
from ._format import format_apis, format_contract, format_run

__all__ = [
    "CleanedWebFindAPI",
    "CleanedWebFindInput",
    "CleanedWebGetAPI",
    "CleanedWebGetInput",
    "CleanedWebRunAPI",
    "CleanedWebRunInput",
]


class CleanedWebFindInput(BaseModel):
    """Input for :class:`CleanedWebFindAPI`."""

    site: Optional[str] = Field(
        default=None, description="Website domain, URL or name, e.g. 'github.com' or 'blocket'."
    )
    fields: Optional[List[str]] = Field(
        default=None, description="Field names the records must have, e.g. ['title', 'price']."
    )
    query: Optional[str] = Field(default=None, description="Topic words, e.g. 'used cars' or 'job listings'.")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of matches to return.")


class CleanedWebGetInput(BaseModel):
    """Input for :class:`CleanedWebGetAPI`."""

    api_id: str = Field(description="The api_id (or catalog slug) from cleanedweb_find_api.")


class CleanedWebRunInput(BaseModel):
    """Input for :class:`CleanedWebRunAPI`."""

    api_id: str = Field(description="The api_id from cleanedweb_find_api.")
    endpoint_id: str = Field(description="The endpoint_id from cleanedweb_find_api or cleanedweb_get_api.")
    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="The endpoint's inputs per its input_schema. Send every required input; {} if none.",
    )
    max_items: Optional[int] = Field(
        default=None,
        ge=1,
        description="Stop after this many records. Start small (5-10); raise only after seeing records.",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        description=(
            "Omit for a new run (one is generated and returned). To read a run that is still going, "
            "repeat the same call with the idempotency_key the result returned."
        ),
    )


class CleanedWebFindAPI(CleanedWebBaseTool):
    """Find published CleanedWeb APIs for a website or topic. Needs no API key.

    Setup:
        .. code-block:: bash

            pip install -U langchain-cleanedweb

    Instantiate:
        .. code-block:: python

            from langchain_cleanedweb import CleanedWebFindAPI

            tool = CleanedWebFindAPI()

    Invoke:
        .. code-block:: python

            tool.invoke({"site": "github.com", "fields": ["title", "url"]})
    """

    name: str = "cleanedweb_find_api"
    description: str = FIND_DESCRIPTION
    args_schema: Type[BaseModel] = CleanedWebFindInput

    def _run(
        self,
        site: Optional[str] = None,
        fields: Optional[List[str]] = None,
        query: Optional[str] = None,
        limit: int = 5,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        try:
            apis = self._client().catalog.find(site=site, fields=fields, q=query, limit=limit)
        except CleanedWebError as exc:
            raise tool_error(exc) from exc
        return format_apis(apis)

    async def _arun(
        self,
        site: Optional[str] = None,
        fields: Optional[List[str]] = None,
        query: Optional[str] = None,
        limit: int = 5,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        try:
            async with self._async_client() as client:
                apis = await client.catalog.find(site=site, fields=fields, q=query, limit=limit)
        except CleanedWebError as exc:
            raise tool_error(exc) from exc
        return format_apis(apis)


class CleanedWebGetAPI(CleanedWebBaseTool):
    """Read one CleanedWeb API's contract (inputs, output fields, sample records). No key needed.

    Invoke:
        .. code-block:: python

            from langchain_cleanedweb import CleanedWebGetAPI

            CleanedWebGetAPI().invoke({"api_id": "generated_047a8ebb25911ccf62f4a212"})
    """

    name: str = "cleanedweb_get_api"
    description: str = GET_DESCRIPTION
    args_schema: Type[BaseModel] = CleanedWebGetInput

    def _run(self, api_id: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> Dict[str, Any]:
        try:
            contract = self._client().catalog.get(api_id)
        except CleanedWebError as exc:
            raise tool_error(exc) from exc
        return format_contract(contract)

    async def _arun(
        self, api_id: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    ) -> Dict[str, Any]:
        try:
            async with self._async_client() as client:
                contract = await client.catalog.get(api_id)
        except CleanedWebError as exc:
            raise tool_error(exc) from exc
        return format_contract(contract)


class CleanedWebRunAPI(CleanedWebBaseTool):
    """Run a CleanedWeb catalog API and return its records. Needs ``CLEANEDWEB_API_KEY``.

    Runs are charged per record delivered (5,000 records free once, then prepaid credit).

    Instantiate:
        .. code-block:: python

            from langchain_cleanedweb import CleanedWebRunAPI

            tool = CleanedWebRunAPI(max_items_limit=50)  # reads CLEANEDWEB_API_KEY

    Invoke:
        .. code-block:: python

            tool.invoke(
                {
                    "api_id": "generated_047a8ebb25911ccf62f4a212",
                    "endpoint_id": "generated_047a8ebb25911ccf62f4a212_search",
                    "input": {"sort": "desc_stars"},
                    "max_items": 5,
                }
            )

    The tool waits up to ``wait_seconds`` for the run to end, then returns ``status: running``
    with the ``idempotency_key``; calling again with that key reads the same run.
    """

    name: str = "cleanedweb_run_api"
    description: str = RUN_DESCRIPTION
    args_schema: Type[BaseModel] = CleanedWebRunInput

    default_max_items: int = Field(default=5, ge=1, description="max_items used when the model gives none.")
    max_items_limit: int = Field(
        default=100, ge=1, description="Upper bound on max_items, to protect the user's credit."
    )
    wait_seconds: int = Field(default=60, ge=0, description="How long one call waits for the run to end.")

    def _max_items(self, requested: Optional[int]) -> int:
        return min(requested or self.default_max_items, self.max_items_limit)

    def _run(
        self,
        api_id: str,
        endpoint_id: str,
        input: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        try:
            result = self._client().catalog.run(
                api_id,
                endpoint_id,
                input or {},
                max_items=self._max_items(max_items),
                idempotency_key=idempotency_key,
                wait_seconds=self.wait_seconds,
                poll_timeout=self.wait_seconds,
            )
        except CleanedWebError as exc:
            raise tool_error(exc) from exc
        except ValueError as exc:  # e.g. an idempotency key the client refuses to send
            raise ToolException(str(exc)) from exc
        return format_run(result)

    async def _arun(
        self,
        api_id: str,
        endpoint_id: str,
        input: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        try:
            async with self._async_client() as client:
                result = await client.catalog.run(
                    api_id,
                    endpoint_id,
                    input or {},
                    max_items=self._max_items(max_items),
                    idempotency_key=idempotency_key,
                    wait_seconds=self.wait_seconds,
                    poll_timeout=self.wait_seconds,
                )
        except CleanedWebError as exc:
            raise tool_error(exc) from exc
        except ValueError as exc:  # e.g. an idempotency key the client refuses to send
            raise ToolException(str(exc)) from exc
        return format_run(result)
