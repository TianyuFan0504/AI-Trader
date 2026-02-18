"""
Simple Tool Registry - Lightweight tool system for AI agents.

Tools are registered via @tool decorator. Imports from skills folder using direct file imports.
"""

import inspect
import sys
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, get_type_hints


def _get_type_name(t) -> str:
    """Get type name, handling generics."""
    origin = getattr(t, "__origin__", None)
    args = getattr(t, "__args__", ())

    if origin is not None:
        if origin is type(None):
            return "null"
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _get_type_name(non_none[0])
        return "string"

    name = getattr(t, "__name__", str.__name__)
    if name == "str":
        return "string"
    if name in ("int", "float"):
        return "number"
    if name == "bool":
        return "boolean"
    return name


@dataclass
class Tool:
    """Tool definition."""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)

    def __post_init__(self):
        sig = inspect.signature(self.func)
        hints = {}
        try:
            hints = get_type_hints(self.func)
        except Exception:
            pass

        for name, param in sig.parameters.items():
            param_type = hints.get(name, str)
            param_info = {"type": _get_type_name(param_type), "description": ""}
            if param.default is inspect.Parameter.empty:
                self.required.append(name)
            self.parameters[name] = param_info

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    name: {"type": info["type"], "description": info["description"]}
                    for name, info in self.parameters.items()
                },
                "required": self.required
            }
        }


class ToolRegistry:
    """Central tool registry."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str = None, description: str = "") -> Callable:
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool = Tool(
                name=tool_name,
                description=description or func.__doc__.split('\n')[0] if func.__doc__ else "",
                func=func
            )
            self._tools[tool_name] = tool
            return func
        return decorator

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_all(self) -> List[Tool]:
        return list(self._tools.values())

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def to_openai_format(self) -> List[Dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    def clear(self):
        self._tools.clear()


registry = ToolRegistry()


def tool(name: str = None, description: str = "") -> Callable:
    """Decorator to register a function as a tool."""
    return registry.register(name, description)


def get_tool(name: str) -> Optional[Tool]:
    return registry.get(name)


def list_tools() -> List[Tool]:
    return registry.list_all()


def list_tool_names() -> List[str]:
    return registry.list_names()


def get_all_schemas() -> List[Dict[str, Any]]:
    return registry.to_openai_format()


def clear_tools():
    registry.clear()


# =============================================================================
# Load tools from skills folder and register them
# =============================================================================

_skills_root = Path(__file__).resolve().parent.parent / "skills"


def _load_module(rel_path: str):
    """Load a Python module from skills folder."""
    spec = importlib.util.spec_from_file_location(
        "skill_module",
        _skills_root / rel_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Math tools
_math = _load_module("math-skill/scripts/math.py")
registry.register("add", "Add two numbers")(_math.add)
registry.register("multiply", "Multiply two numbers")(_math.multiply)

# Price tools
_price = _load_module("price-skill/scripts/price.py")
registry.register("get_price", "Get OHLCV price for a specific date")(_price.get_price)
registry.register("get_prices_range", "Get price history over a date range")(_price.get_prices_range)
registry.register("get_latest_price", "Get current market price")(_price.get_latest_price)
registry.register("search_symbol", "Search for stock symbols")(_price.search_symbol)

# Trading tools
_trading = _load_module("trading-skill/scripts/trading.py")
registry.register("buy", "Buy stocks")(_trading.buy)
registry.register("sell", "Sell stocks")(_trading.sell)
registry.register("buy_crypto", "Buy cryptocurrency")(_trading.buy_crypto)
registry.register("sell_crypto", "Sell cryptocurrency")(_trading.sell_crypto)

# News tools
_news = _load_module("news-skill/scripts/news.py")
registry.register("get_market_news", "Get market news articles")(_news.get_market_news)
