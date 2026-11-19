# langchain-cleanedweb

LangChain tools for [CleanedWeb](https://cleanedweb.com/?utm_source=github&utm_medium=langchain-cleanedweb),
which turns public website collections (listings, products, jobs, articles, profiles) into maintained
REST APIs that return structured records. Three tools let an agent **find** a published API, **read** its
contract, and **run** it, plus a toolkit that bundles them.

**Pricing:** 5,000 records free once, then prepaid credit from $1 per 1,000 records, no subscription.
Runs are charged per record delivered.
[Pricing](https://cleanedweb.com/pricing/?utm_source=github&utm_medium=langchain-cleanedweb)

## Install

```bash
pip install -U langchain-cleanedweb
```

> This repository is private and the packages are not on PyPI yet. Until they are, install the client
> from its checkout first: `pip install -e ../cleanedweb-python` (or
> `pip install git+https://github.com/cleanedweb/cleanedweb-python`), then `pip install -e .` here.
> `langchain-cleanedweb` depends on [`cleanedweb`](https://github.com/cleanedweb/cleanedweb-python).

Create an API key with the `run` scope in the [console](https://app.cleanedweb.com/) and export it as
`CLEANEDWEB_API_KEY`. Finding and reading APIs needs no key.

## Quick start

```python
# pip install langchain
from langchain.agents import create_agent
from langchain_cleanedweb import CleanedWebToolkit

tools = CleanedWebToolkit().get_tools()  # find, get, run (reads CLEANEDWEB_API_KEY)
agent = create_agent("anthropic:claude-sonnet-4-5", tools=tools)
agent.invoke({"messages": [("user", "Get 5 trending Python repositories from GitHub topics.")]})
```

Or call a tool directly:

```python
from langchain_cleanedweb import CleanedWebFindAPI, CleanedWebGetAPI, CleanedWebRunAPI

found = CleanedWebFindAPI().invoke({"site": "github.com", "fields": ["title", "url"]})
api = found["matches"][0]
contract = CleanedWebGetAPI().invoke({"api_id": api["api_id"]})
records = CleanedWebRunAPI(max_items_limit=25).invoke(
    {"api_id": api["api_id"], "endpoint_id": api["endpoints"][0]["endpoint_id"], "max_items": 5}
)
```

## Tools

| Tool | Name | Needs key | What it does |
| --- | --- | --- | --- |
| `CleanedWebFindAPI` | `cleanedweb_find_api` | no | Find published APIs by `site`, `fields`, `query`. Nothing runs. |
| `CleanedWebGetAPI` | `cleanedweb_get_api` | no | Inputs, output fields, limitations and three saved sample records. |
| `CleanedWebRunAPI` | `cleanedweb_run_api` | yes (`run`) | Run an endpoint and return its records. Charged per record. |

The tool descriptions tell the model to find before it runs, to start with a small `max_items`, and that
records are website data, never instructions. `CleanedWebRunAPI` also enforces it: `max_items` defaults to
`default_max_items=5` and is capped by `max_items_limit=100` (both settable). A run that is still going
after `wait_seconds` (default 60) returns `status: running` with its `idempotency_key`; calling the tool
again with the same arguments and key reads the same run and never starts or charges a second one.
Errors (no credit, rate limit, failed run, lost connection) come back as short, actionable text for the
model (`handle_tool_error`). `CleanedWebToolkit(read_only=True)` leaves out the run tool.

Tools work with `invoke` and `ainvoke`. Pass `api_key=`, `base_url=` or a configured
`cleanedweb.CleanedWeb` as `client=` to override the defaults.

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ../cleanedweb-python -e ".[test,lint]"
ruff check . && ruff format --check . && mypy && pytest
pytest tests/integration_tests -m live      # standard integration tests, no-key catalog reads only
```

Unit tests mock the HTTP layer and include LangChain's standard `ToolsUnitTests`.

## More

- [Python guide](https://cleanedweb.com/docs/python/?utm_source=github&utm_medium=langchain-cleanedweb),
  [run a catalog API](https://cleanedweb.com/docs/run-catalog-api/?utm_source=github&utm_medium=langchain-cleanedweb)
- Prefer MCP? The hosted server is [cleanedweb/cleanedweb-mcp](https://github.com/cleanedweb/cleanedweb-mcp).

MIT licensed.
