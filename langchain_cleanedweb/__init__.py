"""LangChain integration for CleanedWeb: maintained REST APIs that return structured records."""

from importlib import metadata

from .toolkit import CleanedWebToolkit
from .tools import CleanedWebFindAPI, CleanedWebGetAPI, CleanedWebRunAPI

try:
    __version__ = metadata.version(__package__ or "langchain-cleanedweb")
except metadata.PackageNotFoundError:  # not installed (e.g. run from a source checkout)
    __version__ = ""
del metadata

__all__ = [
    "CleanedWebFindAPI",
    "CleanedWebGetAPI",
    "CleanedWebRunAPI",
    "CleanedWebToolkit",
    "__version__",
]
