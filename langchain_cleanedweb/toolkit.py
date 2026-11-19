"""A toolkit bundling the CleanedWeb find, get and run tools."""

from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.tools import BaseTool, BaseToolkit
from langchain_core.utils import secret_from_env
from pydantic import ConfigDict, Field, SecretStr

from .tools import CleanedWebFindAPI, CleanedWebGetAPI, CleanedWebRunAPI


class CleanedWebToolkit(BaseToolkit):
    """Tools for finding, reading and running CleanedWeb catalog APIs.

    Setup:
        .. code-block:: bash

            pip install -U langchain-cleanedweb
            export CLEANEDWEB_API_KEY="..."   # only needed to run APIs

    Instantiate:
        .. code-block:: python

            from langchain_cleanedweb import CleanedWebToolkit

            toolkit = CleanedWebToolkit()
            tools = toolkit.get_tools()  # find, get, run

    Pass ``read_only=True`` to leave out the run tool (find and read only, nothing is charged).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: Optional[SecretStr] = Field(default_factory=secret_from_env("CLEANEDWEB_API_KEY", default=None))
    base_url: Optional[str] = None
    read_only: bool = False
    default_max_items: int = Field(default=5, ge=1)
    max_items_limit: int = Field(default=100, ge=1)
    wait_seconds: int = Field(default=60, ge=0)
    client: Optional[Any] = Field(default=None, exclude=True)

    def get_tools(self) -> List[BaseTool]:
        """Return the find and get tools, plus the run tool unless ``read_only``."""
        shared: dict[str, Any] = {"api_key": self.api_key, "base_url": self.base_url, "client": self.client}
        tools: List[BaseTool] = [CleanedWebFindAPI(**shared), CleanedWebGetAPI(**shared)]
        if not self.read_only:
            tools.append(
                CleanedWebRunAPI(
                    **shared,
                    default_max_items=self.default_max_items,
                    max_items_limit=self.max_items_limit,
                    wait_seconds=self.wait_seconds,
                )
            )
        return tools
