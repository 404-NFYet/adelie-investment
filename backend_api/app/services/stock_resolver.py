"""종목 감지 및 실시간 주가 조회 서비스.

KRX 전체 종목 목록을 캐시하여 메시지에서 종목명/코드를 동적으로 감지하고,
pykrx를 통해 실시간 주가 데이터를 조회한다.
"""

import logging
import re
import threading
from typing import Optional

logger = logging.getLogger("narrative_api.stock_resolver")

# --- 외부 모듈 임포트 (선택적) ---
import sys as _sys
from pathlib import Path as _Path

_PROJECT_ROOT = _Path(__file__).resolve().parent.parent.parent.parent
_PIPELINE_PATH = str(_PROJECT_ROOT / "data_pipeline")
if _PIPELINE_PATH not in _sys.path:
    _sys.path.insert(0, _PIPELINE_PATH)

try:
    from collectors.stock_collector import get_stock_history
    _PYKRX_AVAILABLE = True
except ImportError:
    _PYKRX_AVAILABLE = False

try:
    from collectors.financial_collector import format_fundamentals_for_llm
    _FDR_AVAILABLE = True
except ImportError:
    _FDR_AVAILABLE = False

# --- KRX 종목 캐시 ---
_krx_cache: dict[str, str] = {}  # 종목명 → 코드
_krx_cache_lock = threading.Lock()
_krx_loaded = False


def _load_krx_listing():
    """pykrx로 KRX 전체 종목 목록을 로드하여 캐시 (최초 1회, 이후 재사용)."""
    global _krx_loaded
    if _krx_loaded:
        return
    with _krx_cache_lock:
        if _krx_loaded:
            return
        try:
            from pykrx import stock as pykrx_stock
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            for market in ["KOSPI", "KOSDAQ"]:
                tickers = pykrx_stock.get_market_ticker_list(today, market=market)
                for ticker in tickers:
                    try:
                        name = pykrx_stock.get_market_ticker_name(ticker)
                        if name:
                            _krx_cache[name] = ticker
                    except Exception:
                        pass
            _krx_loaded = True
            logger.info("KRX 종목 목록 로드 완료: %d종목", len(_krx_cache))
        except Exception as e:
            logger.warning("KRX 종목 목록 로드 실패: %s (fallback 사용)", e)
            for name, code in {
                "삼성전자": "005930", "SK하이닉스": "000660", "LG에너지솔루션": "373220",
                "현대차": "005380", "NAVER": "035420", "카카오": "035720",
            }.items():
                _krx_cache[name] = code
            _krx_loaded = True


def detect_stock_codes(message: str) -> list[tuple[str, str]]:
    """메시지에서 종목명/코드를 동적으로 감지하여 (이름, 코드) 리스트 반환."""
    _load_krx_listing()
    found = []
    seen_codes = set()

    # 1) 6자리 숫자 종목 코드 직접 감지
    for code in re.findall(r'\b(\d{6})\b', message):
        if code not in seen_codes:
            found.append((code, code))
            seen_codes.add(code)

    # 2) KRX 종목명 매칭 (긴 이름부터)
    for name in sorted(_krx_cache.keys(), key=len, reverse=True):
        if len(name) >= 2 and name in message:
            code = _krx_cache[name]
            if code not in seen_codes:
                found.append((name, code))
                seen_codes.add(code)
            if len(found) >= 3:
                break

    return found[:3]


def should_auto_visualize(message: str, stock_detected: bool, prev_messages: list[dict] = None) -> bool:
    """메시지 맥락을 기반으로 시각화를 자동 생성해야 하는지 판단."""
    msg = message.lower()

    viz_signals = ["시각화", "차트", "그래프", "보여줘", "그려줘", "시각적", "그림으로", "표로"]
    if any(s in msg for s in viz_signals):
        return True

    if stock_detected:
        data_signals = ["주가", "주식", "등락", "추이", "종가", "시세", "얼마", "수익률", "실적"]
        if any(s in msg for s in data_signals):
            return True

    if prev_messages:
        recent_text = " ".join(m.get("content", "") for m in prev_messages[-4:])
        has_prior_stock = any(name in recent_text for name in list(_krx_cache.keys())[:100])
        if has_prior_stock and any(s in msg for s in viz_signals):
            return True

    return False


def fetch_stock_data_for_context(stock_codes: list[tuple[str, str]]) -> tuple[str, dict]:
    """pykrx로 종목 주가를 조회하여 (컨텍스트 텍스트, 차트용 데이터) 반환."""
    if not _PYKRX_AVAILABLE or not stock_codes:
        return "", {}

    context_lines = []
    chart_data = {}

    for name, code in stock_codes:
        try:
            hist = get_stock_history(code, days=10)
            if not hist or not hist.get("history"):
                continue
            stock_name = hist.get("name", name)
            records = hist["history"]
            latest = records[-1] if records else {}

            context_lines.append(
                f"\n[{stock_name}({code}) 최근 주가]\n"
                f"  최근 종가: {latest.get('close', 0):,.0f}원\n"
                f"  등락률: {latest.get('change_pct', 0):+.2f}%\n"
                + "\n".join(
                    f"  {r['date']}: {r['close']:,.0f}원 ({r.get('change_pct', 0):+.2f}%)"
                    for r in records[-5:]
                )
            )
            chart_data[code] = {"name": stock_name, "history": records}
        except Exception as e:
            logger.debug("주가 조회 실패 (%s): %s", code, e)

    return "\n".join(context_lines), chart_data


def get_fundamentals_text(code: str) -> Optional[str]:
    """FinanceDataReader로 재무 지표 텍스트 반환. 실패 시 None."""
    if not _FDR_AVAILABLE:
        return None
    try:
        text = format_fundamentals_for_llm(code)
        if text and "찾을 수 없습니다" not in text:
            return text
    except Exception as e:
        logger.debug("FDR 재무 지표 실패 (%s): %s", code, e)
    return None
