"""Shared plumbing for the CleanedWeb tools."""

from __future__ import annotations

from typing import Any, Optional

from cleanedweb import (
    APIConnectionError,
    AsyncCleanedWeb,
    CleanedWeb,
    CleanedWebError,
    InsufficientCreditError,
    MissingAPIKeyError,
    RateLimitError,
)
from langchain_core.tools import BaseTool, ToolException
from langchain_core.utils import secret_from_env
from pydantic import ConfigDict, Field, PrivateAttr, SecretStr

# Matches the Python client's own default; kept here so the tools work against a staging origin.
_CLIENT_TIMEOUT = 30.0


def tool_error(exc: CleanedWebError) -> ToolException:
    """Turn a client error into a message the model can act on."""
    text = str(exc)
    key = getattr(exc, "idempotency_key", None)
    if isinstance(exc, MissingAPIKeyError):
        text += " Ask the user to set CLEANEDWEB_API_KEY (a key with the `run` scope)."
    elif isinstance(exc, InsufficientCreditError):
        text += " The user's workspace needs credit; tell the user instead of retrying."
    elif isinstance(exc, RateLimitError) and exc.retry_after is not None:
        text += f" Wait {exc.retry_after:g} seconds before calling again."
    if getattr(exc, "run_failed", False):
        text += " The run failed and that is final for its idempotency key: use a new key to run again."
    elif key and (isinstance(exc, APIConnectionError) or getattr(exc, "unsure", False)):
        text += (
            " The run may have started: call cleanedweb_run_api again with the same arguments and "
            f"idempotency_key={key!r} to read it; do not use a new key."
        )
    return ToolException(text)


class CleanedWebBaseTool(BaseTool):
    """Base class: credentials, client construction and error handling."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: Optional[SecretStr] = Field(
        default_factory=secret_from_env("CLEANEDWEB_API_KEY", default=None),
        description="CleanedWeb API key (scope `run`). Defaults to the CLEANEDWEB_API_KEY env var. "
        "Not needed to find or read APIs.",
    )
    base_url: Optional[str] = Field(
        default=None, description="Run origin override; defaults to https://api.cleanedweb.com."
    )
    client: Optional[CleanedWeb] = Field(
        default=None, exclude=True, description="A configured cleanedweb.CleanedWeb client to use."
    )
    handle_tool_error: Any = True

    _sync_client: Optional[CleanedWeb] = PrivateAttr(default=None)

    def _client(self) -> CleanedWeb:
        if self.client is not None:
            return self.client
        if self._sync_client is None:
            self._sync_client = CleanedWeb(
                api_key=self.api_key.get_secret_value() if self.api_key else None,
                base_url=self.base_url,
                timeout=_CLIENT_TIMEOUT,
            )
        return self._sync_client

    def _async_client(self) -> AsyncCleanedWeb:
        """Return a fresh client per call: an httpx async client must not outlive its event loop."""
        return AsyncCleanedWeb(
            api_key=self.api_key.get_secret_value() if self.api_key else None,
            base_url=self.base_url or (self.client.base_url if self.client else None),
            timeout=_CLIENT_TIMEOUT,
        )
