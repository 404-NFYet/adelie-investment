"""호가창 시뮬레이션 유닛 테스트 (8개)."""
import pytest
from app.services.orderbook_simulator import (
    generate_orderbook,
    fill_against_book,
    estimate_fill_probability,
    get_tick_size,
    OrderBookLevel,
)


class TestTickSize:
    """KRX 호가 단위 테스트."""

    def test_low_price_tick(self):
        assert get_tick_size(1500) == 1

    def test_mid_price_tick(self):
        assert get_tick_size(50000) == 50

    def test_high_price_tick(self):
        assert get_tick_size(300000) == 500


class TestGenerateOrderbook:
    """호가창 생성 테스트."""

    def test_spread_increases_with_volatility(self):
        """변동성 ↑ → 스프레드 ↑."""
        ob_low_vol = generate_orderbook(50000, 500000, 0.01, seed=42)
        ob_high_vol = generate_orderbook(50000, 500000, 0.05, seed=42)
        assert ob_high_vol.spread_bps >= ob_low_vol.spread_bps

    def test_spread_decreases_with_volume(self):
        """거래량 ↑ → 스프레드 ↓."""
        ob_low_vol = generate_orderbook(50000, 50000, 0.03, seed=42)
        ob_high_vol = generate_orderbook(50000, 2000000, 0.03, seed=42)
        assert ob_high_vol.spread_bps <= ob_low_vol.spread_bps

    def test_orderbook_has_5_levels(self):
        """기본 5단계 호가."""
        ob = generate_orderbook(50000, 500000, 0.02, seed=1)
        assert len(ob.asks) == 5
        assert len(ob.bids) == 5

    def test_asks_ascending_bids_descending(self):
        """매도 호가 오름차순, 매수 호가 내림차순."""
        ob = generate_orderbook(50000, 500000, 0.02, seed=1)
        for i in range(len(ob.asks) - 1):
            assert ob.asks[i].price <= ob.asks[i + 1].price
        for i in range(len(ob.bids) - 1):
            assert ob.bids[i].price >= ob.bids[i + 1].price


class TestFillAgainstBook:
    """호가 소비 체결 테스트."""

    def test_market_buy_fills_asks(self):
        """시장가 매수 → asks 소비하며 체결."""
        ob = generate_orderbook(50000, 500000, 0.02, seed=42)
        avg_price, filled = fill_against_book(ob.asks, 10, ascending=True)
        assert filled == 10
        assert avg_price > 0
        # 체결가는 현재가 근처
        assert abs(avg_price - 50000) / 50000 < 0.05

    def test_market_sell_fills_bids(self):
        """시장가 매도 → bids 소비하며 체결."""
        ob = generate_orderbook(50000, 500000, 0.02, seed=42)
        avg_price, filled = fill_against_book(ob.bids, 10, ascending=False)
        assert filled == 10
        assert avg_price > 0

    def test_partial_fill_when_insufficient_depth(self):
        """잔량 부족 시 부분 체결."""
        levels = [OrderBookLevel(price=50100, quantity=5)]
        avg_price, filled = fill_against_book(levels, 100, ascending=True)
        assert filled == 5  # 5주만 체결
        assert avg_price == 50100

    def test_empty_book_returns_zero(self):
        """빈 호가 → 0 반환."""
        avg_price, filled = fill_against_book([], 10, ascending=True)
        assert filled == 0
        assert avg_price == 0.0


class TestEstimateFillProbability:
    """지정가 체결 확률 추정 테스트."""

    def test_close_price_high_probability(self):
        """목표가 ≈ 현재가 → 높은 확률."""
        prob = estimate_fill_probability(50000, 50100, 500000, 0.03)
        assert prob >= 0.5

    def test_far_price_low_probability(self):
        """목표가 << 현재가 → 낮은 확률."""
        prob = estimate_fill_probability(40000, 50000, 100000, 0.01)
        assert prob < 0.3

    def test_probability_clamped(self):
        """확률은 0.05~0.95 범위."""
        prob_high = estimate_fill_probability(50000, 50000, 10000000, 0.10)
        prob_low = estimate_fill_probability(10000, 50000, 100, 0.001)
        assert 0.05 <= prob_high <= 0.95
        assert 0.05 <= prob_low <= 0.95
