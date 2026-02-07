"""Morning briefing tool."""

import os
import sys
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "data-pipeline"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


@tool
def get_today_briefing(date: str = None) -> str:
    """
    오늘의 모닝 브리핑을 가져옵니다. 급등주, 급락주, 거래량 상위 종목 정보를 포함합니다.
    
    Args:
        date: 날짜 (YYYYMMDD 형식, 기본값: 오늘)
        
    Returns:
        브리핑 정보 (JSON 형식)
    """
    import json
    
    target_date = date or datetime.now().strftime("%Y%m%d")
    
    try:
        from collectors.stock_collector import (
            get_top_movers,
            get_high_volume_stocks,
            get_market_summary,
        )
        
        # Get data
        movers = get_top_movers(target_date, top_n=5)
        volume = get_high_volume_stocks(target_date, top_n=5)
        market = get_market_summary(target_date)
        
        result = {
            "date": target_date,
            "market_summary": {
                "kospi": market.get("kospi", {}),
                "kosdaq": market.get("kosdaq", {}),
            },
            "top_gainers": [
                {
                    "ticker": item.get("ticker"),
                    "name": item.get("name", "Unknown"),
                    "change_rate": item.get("등락률", 0),
                    "volume": item.get("거래량", 0),
                }
                for item in movers.get("gainers", [])
            ],
            "top_losers": [
                {
                    "ticker": item.get("ticker"),
                    "name": item.get("name", "Unknown"),
                    "change_rate": item.get("등락률", 0),
                    "volume": item.get("거래량", 0),
                }
                for item in movers.get("losers", [])
            ],
            "high_volume": [
                {
                    "ticker": item.get("ticker"),
                    "name": item.get("name", "Unknown"),
                    "volume": item.get("거래량", 0),
                }
                for item in volume.get("high_volume", [])
            ],
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "date": target_date,
            "market_summary": {},
            "top_gainers": [],
            "top_losers": [],
            "high_volume": [],
        }, ensure_ascii=False, indent=2)
