"""호가창 시뮬레이션 모듈.

실제 거래소 호가창 대신, 거래량/변동성 기반으로
매수-매도 스프레드와 잔량을 시뮬레이션한다.
"""

import math
import random
from dataclasses import dataclass


# KRX 가격대별 호가 단위
_TICK_TABLE = [
    (2_000, 1),
    (5_000, 5),
    (20_000, 10),
    (50_000, 50),
    (200_000, 100),
    (500_000, 500),
    (float("inf"), 1_000),
]


def get_tick_size(price: int) -> int:
    """KRX 가격대별 호가 단위 반환."""
    for threshold, tick in _TICK_TABLE:
        if price < threshold:
            return tick
    return 1_000


@dataclass
class OrderBookLevel:
    price: int
    quantity: int


@dataclass
class SimulatedOrderBook:
    asks: list[OrderBookLevel]  # 매도 호가 (낮은 가격순)
    bids: list[OrderBookLevel]  # 매수 호가 (높은 가격순)
    spread_bps: float


def generate_orderbook(
    current_price: int,
    volume: int,
    volatility: float,
    levels: int = 5,
    seed: int | None = None,
) -> SimulatedOrderBook:
    """거래량/변동성 기반 호가창 시뮬레이션 생성.

    Args:
        current_price: 현재가 (원)
        volume: 일 거래량 (주)
        volatility: 일 변동성 (0~1, 예: 0.03 = 3%)
        levels: 호가 단계 수 (기본 5)
        seed: 랜덤 시드 (테스트용)

    Returns:
        SimulatedOrderBook: asks, bids, spread_bps
    """
    rng = random.Random(seed)

    # 스프레드: 변동성 높으면 넓게, 거래량 많으면 좁게
    vol_factor = max(0.5, volatility * 100)  # 0.5~5.0+ 범위
    volume_factor = max(0.5, min(5.0, volume / 500_000))  # 정규화
    base_spread_bps = max(5, min(50, int(vol_factor * 10 / volume_factor)))

    tick = get_tick_size(current_price)

    # 중심가 기준 스프레드 분배
    half_spread_ticks = max(1, base_spread_bps * current_price // (10_000 * tick))
    best_ask = current_price + half_spread_ticks * tick
    best_bid = current_price - half_spread_ticks * tick

    # 잔량: 거래량의 0.5~3%를 단계별 분배 (중심 근처에 많이)
    total_depth = max(100, int(volume * rng.uniform(0.005, 0.03)))
    weights = [math.exp(-0.5 * i) for i in range(levels)]
    weight_sum = sum(weights)

    asks = []
    bids = []
    for i in range(levels):
        level_ratio = weights[i] / weight_sum
        # 약간의 랜덤성 부여
        ask_qty = max(1, int(total_depth * level_ratio * rng.uniform(0.7, 1.3)))
        bid_qty = max(1, int(total_depth * level_ratio * rng.uniform(0.7, 1.3)))
        asks.append(OrderBookLevel(price=best_ask + i * tick, quantity=ask_qty))
        bids.append(OrderBookLevel(price=best_bid - i * tick, quantity=bid_qty))

    return SimulatedOrderBook(
        asks=asks,
        bids=bids,
        spread_bps=base_spread_bps,
    )


def fill_against_book(
    book_levels: list[OrderBookLevel],
    quantity: int,
    ascending: bool = True,
) -> tuple[float, int]:
    """호가 잔량을 소비하며 체결. 가중평균가격과 체결 수량을 반환.

    Args:
        book_levels: 호가 단계 리스트 (정렬 기준은 ascending으로 결정)
        quantity: 주문 수량
        ascending: True면 낮은 가격부터 소비(매수), False면 높은 가격부터(매도)

    Returns:
        (가중평균 체결가, 실제 체결 수량)
    """
    if not book_levels:
        return 0.0, 0

    sorted_levels = sorted(book_levels, key=lambda l: l.price, reverse=not ascending)
    remaining = quantity
    total_cost = 0
    total_filled = 0

    for level in sorted_levels:
        if remaining <= 0:
            break
        fill = min(remaining, level.quantity)
        total_cost += level.price * fill
        total_filled += fill
        remaining -= fill

    if total_filled == 0:
        return 0.0, 0

    avg_price = total_cost / total_filled
    return avg_price, total_filled


def estimate_fill_probability(
    target_price: int,
    current_price: int,
    volume: int,
    volatility: float,
) -> float:
    """지정가 주문의 체결 확률 추정.

    목표가가 현재가에 가까울수록, 변동성이 높을수록,
    거래량이 많을수록 체결 확률이 높다.

    Returns:
        0.05 ~ 0.95 범위의 확률
    """
    if current_price <= 0:
        return 0.05

    # 가격 거리 (비율)
    price_distance = abs(target_price - current_price) / current_price

    # 거리 점수: 0이면 1.0, 멀수록 0에 수렴
    distance_score = math.exp(-price_distance * 50)

    # 변동성 보너스: 높을수록 체결 확률 증가
    vol_score = min(1.0, volatility * 20)

    # 거래량 보너스: 많을수록 체결 확률 증가
    vol_amount_score = min(1.0, volume / 1_000_000)

    # 가중 합산
    raw_prob = 0.5 * distance_score + 0.3 * vol_score + 0.2 * vol_amount_score

    # 클램핑
    return max(0.05, min(0.95, raw_prob))
