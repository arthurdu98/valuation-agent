"""Industry-specific metric plugins."""

from src.data.industry.base import IndustryPlugin
from src.data.industry.baijiu import BaijiuPlugin

__all__ = ["IndustryPlugin", "BaijiuPlugin"]
