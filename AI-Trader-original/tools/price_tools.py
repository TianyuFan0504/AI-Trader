import os

from dotenv import load_dotenv

load_dotenv()
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 将项目根目录加入 Python 路径，便于从子目录直接运行本文件
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from tools.general_tools import get_config_value
from tools.trading_db import (
    get_latest_position as db_get_latest_position,
    append_no_trade_record as db_append_no_trade_record,
    get_db_path, init_db,
    get_all_timestamps, get_timestamps_for_symbol, get_symbols,
    get_prices_range, check_price_exists, add_price
)

def _normalize_timestamp_str(ts: str) -> str:
    """
    Normalize timestamp string to zero-padded HH for robust string/chrono comparisons.
    - If ts has time part like 'YYYY-MM-DD H:MM:SS', pad hour to 'HH'.
    - If ts is date-only, return as-is.
    """
    try:
        if " " not in ts:
            return ts
        date_part, time_part = ts.split(" ", 1)
        parts = time_part.split(":")
        if len(parts) != 3:
            return ts
        hour, minute, second = parts
        hour = hour.zfill(2)
        return f"{date_part} {hour}:{minute}:{second}"
    except Exception:
        return ts

def _parse_timestamp_to_dt(ts: str) -> datetime:
    """
    Parse timestamp string to datetime, supporting both date-only and datetime.
    Assumes ts is already normalized if time exists.
    """
    if " " in ts:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    return datetime.strptime(ts, "%Y-%m-%d")


def get_market_type() -> str:
    """
    智能获取市场类型，支持多种检测方式：
    1. 优先从配置中读取 MARKET
    2. 如果未设置，则根据 LOG_PATH 推断（agent_data_astock -> cn, agent_data_crypto -> crypto, agent_data -> us）
    3. 最后默认为 us

    Returns:
        "cn" for A-shares market, "us" for US market, "crypto" for cryptocurrency market
    """
    # 方式1: 从配置读取
    market = get_config_value("MARKET", None)
    if market in ["cn", "us", "crypto"]:
        return market

    # 方式2: 根据 LOG_PATH 推断
    log_path = get_config_value("LOG_PATH", "./data/agent_data")
    if "astock" in log_path.lower() or "a_stock" in log_path.lower():
        return "cn"
    elif "crypto" in log_path.lower():
        return "crypto"

    # 方式3: 默认为美股
    return "us"


all_nasdaq_100_symbols = [
    "NVDA",
    "MSFT",
    "AAPL",
    "GOOG",
    "GOOGL",
    "AMZN",
    "META",
    "AVGO",
    "TSLA",
    "NFLX",
    "PLTR",
    "COST",
    "ASML",
    "AMD",
    "CSCO",
    "AZN",
    "TMUS",
    "MU",
    "LIN",
    "PEP",
    "SHOP",
    "APP",
    "INTU",
    "AMAT",
    "LRCX",
    "PDD",
    "QCOM",
    "ARM",
    "INTC",
    "BKNG",
    "AMGN",
    "TXN",
    "ISRG",
    "GILD",
    "KLAC",
    "PANW",
    "ADBE",
    "HON",
    "CRWD",
    "CEG",
    "ADI",
    "ADP",
    "DASH",
    "CMCSA",
    "VRTX",
    "MELI",
    "SBUX",
    "CDNS",
    "ORLY",
    "SNPS",
    "MSTR",
    "MDLZ",
    "ABNB",
    "MRVL",
    "CTAS",
    "TRI",
    "MAR",
    "MNST",
    "CSX",
    "ADSK",
    "PYPL",
    "FTNT",
    "AEP",
    "WDAY",
    "REGN",
    "ROP",
    "NXPI",
    "DDOG",
    "AXON",
    "ROST",
    "IDXX",
    "EA",
    "PCAR",
    "FAST",
    "EXC",
    "TTWO",
    "XEL",
    "ZS",
    "PAYX",
    "WBD",
    "BKR",
    "CPRT",
    "CCEP",
    "FANG",
    "TEAM",
    "CHTR",
    "KDP",
    "MCHP",
    "GEHC",
    "VRSK",
    "CTSH",
    "CSGP",
    "KHC",
    "ODFL",
    "DXCM",
    "TTD",
    "ON",
    "BIIB",
    "LULU",
    "CDW",
    "GFS",
]

all_sse_50_symbols = [
    "600519.SH",
    "601318.SH",
    "600036.SH",
    "601899.SH",
    "600900.SH",
    "601166.SH",
    "600276.SH",
    "600030.SH",
    "603259.SH",
    "688981.SH",
    "688256.SH",
    "601398.SH",
    "688041.SH",
    "601211.SH",
    "601288.SH",
    "601328.SH",
    "688008.SH",
    "600887.SH",
    "600150.SH",
    "601816.SH",
    "601127.SH",
    "600031.SH",
    "688012.SH",
    "603501.SH",
    "601088.SH",
    "600309.SH",
    "601601.SH",
    "601668.SH",
    "603993.SH",
    "601012.SH",
    "601728.SH",
    "600690.SH",
    "600809.SH",
    "600941.SH",
    "600406.SH",
    "601857.SH",
    "601766.SH",
    "601919.SH",
    "600050.SH",
    "600760.SH",
    "601225.SH",
    "600028.SH",
    "601988.SH",
    "688111.SH",
    "601985.SH",
    "601888.SH",
    "601628.SH",
    "601600.SH",
    "601658.SH",
    "600048.SH",
]


def get_merged_file_path(market: str = "us") -> Path:
    """Get merged.jsonl path based on market type.

    Args:
        market: Market type, "us" for US stocks, "cn" for A-shares, "crypto" for cryptocurrencies

    Returns:
        Path object pointing to the merged.jsonl file
    """
    base_dir = Path(__file__).resolve().parents[1]
    if market == "cn":
        return base_dir / "data" / "A_stock" / "merged.jsonl"
    elif market == "crypto":
        return base_dir / "data" / "crypto" / "crypto_merged.jsonl"
    else:
        return base_dir / "data" / "merged.jsonl"

def _resolve_merged_file_path_for_date(
    today_date: Optional[str], market: str, merged_path: Optional[str] = None
) -> Path:
    """
    Resolve the correct merged data file path taking into account market and granularity.
    For A-shares:
      - Daily: data/A_stock/merged.jsonl
      - Hourly (timestamp contains space): data/A_stock/merged_hourly.jsonl
    A custom merged_path, if provided, takes precedence.
    """
    if merged_path is not None:
        return Path(merged_path)
    base_dir = Path(__file__).resolve().parents[1]
    if market == "cn" and today_date and " " in today_date:
        # Hourly trading session for A-shares
        return base_dir / "data" / "A_stock" / "merged_hourly.jsonl"
    return get_merged_file_path(market)


def is_trading_day(date: str, market: str = "us") -> bool:
    """Check if a given date is a trading day by looking up database.

    Args:
        date: Date string in "YYYY-MM-DD" format
        market: Market type ("us", "cn", or "crypto")

    Returns:
        True if the date exists in database (is a trading day), False otherwise
    """
    # Initialize database
    db_path = get_db_path("prices")
    init_db(db_path)

    # Get all timestamps from database
    timestamps = get_all_timestamps(market, db_path)

    # Check if any timestamp starts with the date
    for ts in timestamps:
        if ts.startswith(date):
            return True

    return False


def get_all_trading_days(market: str = "us") -> List[str]:
    """Get all available trading days from database.

    Args:
        market: Market type ("us", "cn", "crypto", "astock_hourly")

    Returns:
        Sorted list of trading dates in "YYYY-MM-DD" format
    """
    merged_file_path = get_merged_file_path(market)

    if not merged_file_path.exists():
        print(f"⚠️  Warning: {merged_file_path} not found")
        return []

    trading_days = set()
    try:
        with open(merged_file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    time_series = data.get("Time Series (Daily)", {})
                    # Add all dates from this stock's time series
                    trading_days.update(time_series.keys())
                except json.JSONDecodeError:
                    continue
        return sorted(list(trading_days))
    except Exception as e:
        print(f"⚠️  Error reading trading days: {e}")
        return []


def get_stock_name_mapping(market: str = "us") -> Dict[str, str]:
    """Get mapping from stock symbols to names.

    Args:
        market: Market type ("us" or "cn")

    Returns:
        Dictionary mapping symbols to names, e.g. {"600519.SH": "贵州茅台"}
    """
    merged_file_path = get_merged_file_path(market)

    if not merged_file_path.exists():
        return {}

    name_map = {}
    try:
        with open(merged_file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    meta = data.get("Meta Data", {})
                    symbol = meta.get("2. Symbol")
                    name = meta.get("2.1. Name", "")
                    if symbol and name:
                        name_map[symbol] = name
                except json.JSONDecodeError:
                    continue
        return name_map
    except Exception as e:
        print(f"⚠️  Error reading stock names: {e}")
        return {}


def format_price_dict_with_names(
    price_dict: Dict[str, Optional[float]], market: str = "us"
) -> Dict[str, Optional[float]]:
    """Format price dictionary to include stock names for display.

    Args:
        price_dict: Original price dictionary with keys like "600519.SH_price"
        market: Market type ("us" or "cn")

    Returns:
        New dictionary with keys like "600519.SH (贵州茅台)_price" for CN market,
        unchanged for US market
    """
    if market != "cn":
        return price_dict

    name_map = get_stock_name_mapping(market)
    if not name_map:
        return price_dict

    formatted_dict = {}
    for key, value in price_dict.items():
        if key.endswith("_price"):
            symbol = key[:-6]  # Remove "_price" suffix
            stock_name = name_map.get(symbol, "")
            if stock_name:
                new_key = f"{symbol} ({stock_name})_price"
            else:
                new_key = key
            formatted_dict[new_key] = value
        else:
            formatted_dict[key] = value

    return formatted_dict


def get_yesterday_date(today_date: str, merged_path: Optional[str] = None, market: str = "us") -> str:
    """
    获取输入日期的上一个交易日或时间点。
    从数据库读取所有可用的交易时间，然后找到 today_date 的上一个时间。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS。
        merged_path: 已废弃，保留兼容性
        market: 市场类型，"us" 为美股，"cn" 为A股

    Returns:
        yesterday_date: 上一个交易日或时间点的字符串，格式与输入一致。
    """
    from tools.trading_db import get_all_timestamps, init_db, get_db_path

    # 解析输入日期/时间
    if ' ' in today_date:
        input_dt = datetime.strptime(today_date, "%Y-%m-%d %H:%M:%S")
        date_only = False
    else:
        input_dt = datetime.strptime(today_date, "%Y-%m-%d")
        date_only = True

    # 从数据库获取所有时间戳
    db_path = get_db_path("prices")
    init_db(db_path)
    timestamps = get_all_timestamps(market, db_path)

    if not timestamps:
        # 如果数据库为空，根据输入类型回退
        if date_only:
            yesterday_dt = input_dt - timedelta(days=1)
            while yesterday_dt.weekday() >= 5:
                yesterday_dt -= timedelta(days=1)
            return yesterday_dt.strftime("%Y-%m-%d")
        else:
            yesterday_dt = input_dt - timedelta(hours=1)
            return yesterday_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 将所有时间戳转换为 datetime 对象，并找到小于 today_date 的最大时间戳
    previous_timestamp = None

    for ts_str in timestamps:
        try:
            ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            if ts_dt < input_dt:
                if previous_timestamp is None or ts_dt > previous_timestamp:
                    previous_timestamp = ts_dt
        except Exception:
            continue

    # 如果没有找到更早的时间戳，根据输入类型回退
    if previous_timestamp is None:
        if date_only:
            yesterday_dt = input_dt - timedelta(days=1)
            while yesterday_dt.weekday() >= 5:
                yesterday_dt -= timedelta(days=1)
            return yesterday_dt.strftime("%Y-%m-%d")
        else:
            yesterday_dt = input_dt - timedelta(hours=1)
            return yesterday_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 返回结果
    if date_only:
        return previous_timestamp.strftime("%Y-%m-%d")
    else:
        return previous_timestamp.strftime("%Y-%m-%d %H:%M:%S")





def get_open_prices(
    today_date: str, symbols: List[str], merged_path: Optional[str] = None, market: str = "us"
) -> Dict[str, Optional[float]]:
    """从数据库读取指定日期与标的的开盘价。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD或YYYY-MM-DD HH:MM:SS。
        symbols: 需要查询的股票代码列表。
        merged_path: 已废弃，保留兼容性
        market: 市场类型，"us" 为美股，"cn" 为A股

    Returns:
        {symbol_price: open_price 或 None} 的字典；若未找到对应日期或标的，则值为 None。
    """
    from tools.trading_db import get_prices_range, init_db, get_db_path

    wanted = set(symbols)
    results: Dict[str, Optional[float]] = {}

    # 初始化数据库
    db_path = get_db_path("prices")
    init_db(db_path)

    # 构建日期范围 (当天 00:00:00 到 23:59:59)
    if ' ' in today_date:
        # 如果已经有时间戳，直接使用
        start_time = today_date
        end_time = today_date
    else:
        # 只用日期，查询当天所有时间点
        start_time = f"{today_date} 00:00:00"
        end_time = f"{today_date} 23:59:59"

    # 对于每个股票，从数据库获取当天价格
    for sym in wanted:
        prices = get_prices_range(sym, start_time, end_time, market, db_path)
        if prices:
            # 取第一个价格作为开盘价
            first_price = prices[0]
            results[f"{sym}_price"] = first_price.get("buy_price")
        else:
            results[f"{sym}_price"] = None

    return results


def get_yesterday_open_and_close_price(
    today_date: str, symbols: List[str], merged_path: Optional[str] = None, market: str = "us"
) -> Tuple[Dict[str, Optional[float]], Dict[str, Optional[float]]]:
    """从数据库读取指定日期与股票的昨日买入价和卖出价。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        symbols: 需要查询的股票代码列表。
        merged_path: 已废弃，保留兼容性
        market: 市场类型，"us" 为美股，"cn" 为A股

    Returns:
        (买入价字典, 卖出价字典) 的元组；若未找到对应日期或标的，则值为 None。
    """
    from tools.trading_db import get_prices_range, init_db, get_db_path

    wanted = set(symbols)
    buy_results: Dict[str, Optional[float]] = {}
    sell_results: Dict[str, Optional[float]] = {}

    # 获取昨日日期
    yesterday_date = get_yesterday_date(today_date, merged_path=merged_path, market=market)

    # 初始化数据库
    db_path = get_db_path("prices")
    init_db(db_path)

    # 构建昨日日期范围
    if ' ' in yesterday_date:
        start_time = yesterday_date
        end_time = yesterday_date
    else:
        start_time = f"{yesterday_date} 00:00:00"
        end_time = f"{yesterday_date} 23:59:59"

    # 对于每个股票，从数据库获取昨日价格
    for sym in wanted:
        prices = get_prices_range(sym, start_time, end_time, market, db_path)
        if prices:
            # 取第一个价格作为开盘价（买入价），最后一个作为收盘价（卖出价）
            first_price = prices[0]
            last_price = prices[-1]
            buy_results[f"{sym}_price"] = first_price.get("buy_price")
            sell_results[f"{sym}_price"] = last_price.get("sell_price")
        else:
            buy_results[f"{sym}_price"] = None
            sell_results[f"{sym}_price"] = None

    return buy_results, sell_results



def get_yesterday_profit(
    today_date: str,
    yesterday_buy_prices: Dict[str, Optional[float]],
    yesterday_sell_prices: Dict[str, Optional[float]],
    yesterday_init_position: Dict[str, float],
    stock_symbols: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    获取持仓收益（适用于日线和小时级交易）
    
    收益计算方式为：(前一时间点收盘价 - 前一时间点开盘价) × 当前持仓数量
    
    对于日线交易：计算昨日的收益
    对于小时级交易：计算上一小时的收益
    
    Args:
        today_date: 日期/时间字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        yesterday_buy_prices: 前一时间点开盘价格字典，格式为 {symbol_price: price}
        yesterday_sell_prices: 前一时间点收盘价格字典，格式为 {symbol_price: price}
        yesterday_init_position: 前一时间点初始持仓字典，格式为 {symbol: quantity}
        stock_symbols: 股票代码列表，默认为 all_nasdaq_100_symbols

    Returns:
        {symbol: profit} 的字典；若未找到对应日期或标的，则值为 0.0。
    """
    profit_dict = {}

    # 使用传入的股票列表或默认的纳斯达克100列表
    if stock_symbols is None:
        stock_symbols = all_nasdaq_100_symbols

    # 遍历所有股票代码
    for symbol in stock_symbols:
        symbol_price_key = f"{symbol}_price"

        # 获取昨日开盘价和收盘价
        buy_price = yesterday_buy_prices.get(symbol_price_key)
        sell_price = yesterday_sell_prices.get(symbol_price_key)

        # 获取昨日持仓权重
        position_weight = yesterday_init_position.get(symbol, 0.0)

        # 计算收益：(收盘价 - 开盘价) * 持仓权重
        if buy_price is not None and sell_price is not None and position_weight > 0:
            profit = (sell_price - buy_price) * position_weight
            profit_dict[symbol] = round(profit, 4)  # 保留4位小数
        else:
            profit_dict[symbol] = 0.0

    return profit_dict

def get_today_init_position(today_date: str, signature: str) -> Dict[str, float]:
    """
    获取今日开盘时的初始持仓（即数据库中上一个交易日代表的持仓）。
    如果同一日期有多条记录，选择id最大的记录作为初始持仓。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        signature: 模型名称，用于构建文件路径。

    Returns:
        {symbol: weight} 的字典；若未找到对应日期，则返回空字典。
    """
    from tools.general_tools import get_config_value
    from tools.trading_db import get_position_history, get_db_path, init_db

    # Get log_path from config
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    # Determine market for database
    if "astock" in str(log_path).lower():
        db_market = "astock"
    elif "crypto" in str(log_path).lower():
        db_market = "crypto"
    else:
        db_market = "agent_data"

    # Initialize database
    db_path = get_db_path(db_market)
    init_db(db_path)

    # Get position history from database
    all_records = get_position_history(signature, db_path)

    if not all_records:
        return {}

    # Filter records with date < today_date
    filtered_records = [
        r for r in all_records
        if r.get("date") and r.get("date") < today_date
    ]

    if not filtered_records:
        return {}

    # Sort by date (descending) then by id (descending) to get the most recent record
    filtered_records.sort(
        key=lambda x: (x.get("date", ""), x.get("id", 0)),
        reverse=True
    )

    return filtered_records[0].get("positions", {})


def get_latest_position(today_date: str, signature: str) -> Tuple[Dict[str, float], int]:
    """
    获取最新持仓。从数据库中读取。
    优先选择当天 (today_date) 中 id 最大的记录；
    若当天无记录，则回退到上一个交易日，选择该日中 id 最大的记录。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        signature: 模型名称，用于构建文件路径。

    Returns:
        (positions, max_id):
          - positions: {symbol: weight} 的字典；若未找到任何记录，则为空字典。
          - max_id: 选中记录的最大 id；若未找到任何记录，则为 -1.
    """
    from tools.general_tools import get_config_value
    import os

    # Get log_path from config
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    # Determine market for database
    if "astock" in str(log_path).lower():
        db_market = "astock"
    elif "crypto" in str(log_path).lower():
        db_market = "crypto"
    else:
        db_market = "agent_data"

    # Initialize database
    db_path = get_db_path(db_market)
    init_db(db_path)

    # 获取市场类型，智能判断
    market = get_market_type()

    # Step 1: 先查找当天的记录
    from tools.trading_db import get_position_history

    all_records = get_position_history(signature, db_path)

    # Filter for today's records
    today_records = [r for r in all_records if r.get("date") == today_date]

    if today_records:
        # Get record with max id for today
        latest = max(today_records, key=lambda x: x.get("id", 0))
        return latest.get("positions", {}), latest.get("id", -1)

    # Step 2: 当天没有记录，则回退到上一个交易日
    prev_date = get_yesterday_date(today_date, market=market)

    prev_records = [r for r in all_records if r.get("date") == prev_date]

    if prev_records:
        # Get record with max id for previous day
        latest = max(prev_records, key=lambda x: x.get("id", 0))
        return latest.get("positions", {}), latest.get("id", -1)

    # Step 3: 如果前一天也没有记录，尝试找最新的非空记录（按实际时间和id排序）
    norm_today = _normalize_timestamp_str(today_date)
    today_dt = _parse_timestamp_to_dt(norm_today)

    valid_records = [
        r for r in all_records
        if r.get("positions") and _parse_timestamp_to_dt(_normalize_timestamp_str(r.get("date", "1900-01-01"))) < today_dt
    ]

    if valid_records:
        # 先按实际时间排序，再按id排序，取最新的一条
        valid_records.sort(
            key=lambda x: (
                _parse_timestamp_to_dt(_normalize_timestamp_str(x.get("date", "1900-01-01"))),
                x.get("id", 0),
            ),
            reverse=True,
        )
        latest = valid_records[0]
        return latest.get("positions", {}), latest.get("id", -1)

    return {}, -1

def add_no_trade_record(today_date: str, signature: str):
    """
    添加不交易记录到数据库。
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        signature: 模型名称，用于构建文件路径。

    Returns:
        None
    """
    # Get log_path from config
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    # Determine market for database
    if "astock" in str(log_path).lower():
        db_market = "astock"
    elif "crypto" in str(log_path).lower():
        db_market = "crypto"
    else:
        db_market = "agent_data"

    # Initialize database
    db_path = get_db_path(db_market)
    init_db(db_path)

    # Get latest position
    current_position, current_action_id = db_get_latest_position(signature, db_path, db_market)

    # Append no trade record
    db_append_no_trade_record(
        signature=signature,
        date=today_date,
        positions=current_position,
        current_id=current_action_id,
        db_path=db_path,
        market=db_market
    )
    return


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(today_date, signature)
    yesterday_date = get_yesterday_date(today_date)
    print(yesterday_date)
    # today_buy_price = get_open_prices(today_date, all_nasdaq_100_symbols)
    # print(today_buy_price)
    # yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(today_date, all_nasdaq_100_symbols)
    # print(yesterday_sell_prices)
    # today_init_position = get_today_init_position(today_date, signature='qwen3-max')
    # print(today_init_position)
    # latest_position, latest_action_id = get_latest_position('2025-10-24', 'qwen3-max')
    # print(latest_position, latest_action_id)
    latest_position, latest_action_id = get_latest_position('2025-10-16 16:00:00', 'test')
    print(latest_position, latest_action_id)
    
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    # # print(yesterday_profit)
    # add_no_trade_record(today_date, signature)
