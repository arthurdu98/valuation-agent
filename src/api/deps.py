"""Shared dependencies and helpers for API routers."""

from __future__ import annotations

from functools import lru_cache

from src.data.company_manager import CompanyManager
from src.data.industry.baijiu import BaijiuPlugin
from src.data.industry.internet import InternetPlugin
from src.data.industry.tcm import TCMPlugin
from src.data.industry.toy import ToyPlugin
from src.api.run_registry import registry


@lru_cache(maxsize=1)
def get_company_manager() -> CompanyManager:
    """Return the shared CompanyManager (state lives in a class-level dict)."""
    return CompanyManager()


def get_run_registry():
    """Return the process-local run registry singleton."""
    return registry


# Industry name (Chinese) -> plugin instance. Plugins are stateless singletons.
_INDUSTRY_PLUGINS = {
    "白酒": BaijiuPlugin(),
    "互联网": InternetPlugin(),
    "中药": TCMPlugin(),
    "潮玩": ToyPlugin(),
}


def get_industry_plugin(industry: str):
    """Return the plugin for an industry, or None if unsupported."""
    return _INDUSTRY_PLUGINS.get(industry)


def available_industries() -> list[str]:
    return list(_INDUSTRY_PLUGINS.keys())
