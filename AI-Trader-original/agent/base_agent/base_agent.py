"""
BaseAgent class - Base class for trading agents.

Uses a simple tool system (no LangChain/MCP dependency).
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from tools import get_all_schemas, get_tool
from tools.general_tools import (
    extract_conversation, extract_tool_messages,
    get_config_value, write_config_value
)
from tools.price_tools import add_no_trade_record
from tools.trading_db import (
    init_db, get_latest_position, append_position, append_no_trade_record,
    get_position_history, check_position_exists, get_db_path, append_log
)

# Load environment variables
load_dotenv()


class SimpleAgent:
    """Simple agent that uses OpenAI-compatible API with registered tools."""

    def __init__(
        self,
        signature: str,
        basemodel: str,
        stock_symbols: Optional[List[str]] = None,
        log_path: Optional[str] = None,
        max_steps: int = 10,
        openai_base_url: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        initial_cash: float = 10000.0,
        init_date: str = "2025-10-13",
        market: str = "us"
    ):
        """Initialize the agent."""
        self.signature = signature
        self.basemodel = basemodel
        self.market = market
        self.max_steps = max_steps
        self.initial_cash = initial_cash
        self.init_date = init_date

        # Auto-select stock symbols
        if stock_symbols is None:
            if market == "cn":
                from prompts.agent_prompt import all_sse_50_symbols
                self.stock_symbols = all_sse_50_symbols
            else:
                self.stock_symbols = self._default_us_symbols()
        else:
            self.stock_symbols = stock_symbols

        # OpenAI config
        self.openai_base_url = openai_base_url or os.getenv("OPENAI_API_BASE")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not set")

        # Log path
        self.base_log_path = log_path or "./data/agent_data"
        self.data_path = os.path.join(self.base_log_path, self.signature)

        # Database setup
        if "astock" in str(self.base_log_path).lower():
            self._db_market = "astock"
        elif "crypto" in str(self.base_log_path).lower():
            self._db_market = "crypto"
        else:
            self._db_market = "agent_data"

        self._db_path = get_db_path(self._db_market)
        init_db(self._db_path)

        # Tool schemas for API
        self.tool_schemas = get_all_schemas()

        # API client (set in run)
        self.client = None

    def _default_us_symbols(self) -> List[str]:
        """Default US stock symbols (NASDAQ 100)."""
        return [
            "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO",
            "TSLA", "NFLX", "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN",
            "TMUS", "MU", "LIN", "PEP", "SHOP", "APP", "INTU", "AMAT",
            "LRCX", "PDD", "QCOM", "ARM", "INTC", "BKNG", "AMGN", "TXN",
            "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON", "CRWD", "CEG",
            "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX", "CDNS",
            "ORLY", "SNPS", "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI",
            "MAR", "MNST", "CSX", "ADSK", "PYPL", "FTNT", "AEP", "WDAY",
            "REGN", "ROP", "NXPI", "DDOG", "AXON", "ROST", "IDXX", "EA",
            "PCAR", "FAST", "EXC", "TTWO", "XEL", "ZS", "PAYX", "WBD",
            "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR", "KDP", "MCHP",
            "GEHC", "VRSK", "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD",
            "ON", "BIIB", "LULU", "CDW", "GFS"
        ]

    def _setup_logging(self, today_date: str) -> str:
        """Set up log file path."""
        log_path = os.path.join(self.base_log_path, self.signature, "log", today_date)
        if not os.path.exists(log_path):
            os.makedirs(log_path)
        return os.path.join(log_path, "log.jsonl")

    def _log_message(self, log_file: str, new_messages: List[Dict[str, str]]) -> None:
        """Log messages to file."""
        log_entry = {
            "signature": self.signature,
            "new_messages": new_messages
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    async def call_api(self, messages: List[Dict], tools: bool = True) -> Dict:
        """Call OpenAI-compatible API."""
        import httpx

        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.basemodel,
            "messages": messages,
            "max_tokens": 4096
        }

        if tools and self.tool_schemas:
            payload["tools"] = self.tool_schemas

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.openai_base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    def execute_tool(self, name: str, args: Dict) -> Any:
        """Execute a registered tool."""
        tool = get_tool(name)
        if tool is None:
            return {"error": f"Unknown tool: {name}"}
        return tool.func(**args)

    async def run_session(self, today_date: str) -> None:
        """Run a trading session."""
        print(f"📈 Running session: {self.signature} - {today_date}")

        # Set config
        write_config_value("TODAY_DATE", today_date)
        write_config_value("SIGNATURE", self.signature)

        log_file = self._setup_logging(today_date)

        # Get system prompt
        from prompts.agent_prompt import get_agent_system_prompt
        system_prompt = get_agent_system_prompt(today_date, self.signature, self.market, self.stock_symbols)

        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": f"Please analyze and update positions for {today_date}."})

        self._log_message(log_file, messages[-1:])

        step = 0
        while step < self.max_steps:
            step += 1
            print(f"🔄 Step {step}/{self.max_steps}")

            # Call API
            response = await self.call_api(messages)

            choice = response["choices"][0]
            message = choice["message"]

            # Check for stop signal
            from prompts.agent_prompt import STOP_SIGNAL
            if STOP_SIGNAL in message.get("content", ""):
                print("✅ Stop signal received")
                break

            # Handle tool calls
            if "tool_calls" in message:
                tool_calls = message["tool_calls"]
                tool_results = []

                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    arguments = json.loads(tc["function"]["arguments"])

                    print(f"   🔧 Calling {tool_name}: {arguments}")
                    try:
                        result = self.execute_tool(tool_name, arguments)
                        print(f"   ✅ Result: {str(result)[:100]}...")
                    except Exception as e:
                        result = {"error": str(e)}
                        print(f"   ❌ Error: {e}")

                    tool_results.append({
                        "tool_call_id": tc["id"],
                        "role": "tool",
                        "name": tool_name,
                        "content": str(result)
                    })

                # Add assistant message and tool results
                messages.append({
                    "role": "assistant",
                    "content": message.get("content", ""),
                    "tool_calls": tool_calls
                })
                messages.extend(tool_results)
            else:
                # No tool calls, regular response
                messages.append({"role": "assistant", "content": message.get("content", "")})
                self._log_message(log_file, [{"role": "assistant", "content": message.get("content", "")}])
                break

        # Handle results
        if_trade = get_config_value("IF_TRADE")
        if if_trade:
            write_config_value("IF_TRADE", False)
            print("✅ Trading completed")
        else:
            print("📊 No trading")
            add_no_trade_record(today_date, self.signature)
            write_config_value("IF_TRADE", False)

    def register(self) -> None:
        """Register agent with initial position."""
        if check_position_exists(self.signature, self._db_path):
            print(f"⚠️ {self.signature} already registered")
            return

        init_position = {s: 0 for s in self.stock_symbols}
        init_position["CASH"] = self.initial_cash

        append_position(
            signature=self.signature, date=self.init_date, action_type="init",
            symbol="", amount=0, positions=init_position,
            db_path=self._db_path, market=self._db_market
        )

        currency = "¥" if self.market == "cn" else "$"
        print(f"✅ {self.signature} registered with {currency}{self.initial_cash:,.2f}")


# Keep backward compatibility - BaseAgent now points to SimpleAgent
BaseAgent = SimpleAgent
