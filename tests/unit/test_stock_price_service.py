"""Unit tests for stock price source selection and cache behavior."""

import json

import pytest

from app.services import stock_price_service


class _FakeRedisClient:
    def __init__(self, cached=None):
        self.cached = cached
        self.setex_calls = []

    async def get(self, _key):
        return self.cached

    async def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))


class _FakeCache:
    def __init__(self, client):
        self.client = client


@pytest.mark.asyncio
async def test_get_current_price_uses_cached_value_first(monkeypatch):
    cached = json.dumps({
        "stock_code": "005930",
        "stock_name": "삼성전자",
        "current_price": 71000,
        "change_rate": 1.23,
        "volume": 100,
        "timestamp": "20260219",
        "source": "kis",
    })

    fake_cache = _FakeCache(_FakeRedisClient(cached=cached))

    async def _fake_get_redis_cache():
        return fake_cache

    async def _fake_fetch_kis(_stock_code):
        raise AssertionError("KIS fetch should not run when cache hit exists")

    monkeypatch.setattr(stock_price_service, "get_redis_cache", _fake_get_redis_cache)
    monkeypatch.setattr(stock_price_service, "_fetch_price_from_kis", _fake_fetch_kis)

    result = await stock_price_service.get_current_price("005930")
    assert result["current_price"] == 71000
    assert result["source"] == "kis"


@pytest.mark.asyncio
async def test_get_current_price_prefers_kis_before_pykrx(monkeypatch):
    fake_cache = _FakeCache(_FakeRedisClient())

    async def _fake_get_redis_cache():
        return fake_cache

    async def _fake_fetch_kis(_stock_code):
        return {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "current_price": 72000,
            "change_rate": 2.0,
            "volume": 321,
            "timestamp": "20260219103000",
            "source": "kis",
        }

    async def _fake_wait_for(*_args, **_kwargs):
        raise AssertionError("pykrx fallback should not run when KIS succeeds")

    monkeypatch.setattr(stock_price_service, "get_redis_cache", _fake_get_redis_cache)
    monkeypatch.setattr(stock_price_service, "_fetch_price_from_kis", _fake_fetch_kis)
    monkeypatch.setattr(stock_price_service.asyncio, "wait_for", _fake_wait_for)

    result = await stock_price_service.get_current_price("005930")
    assert result["current_price"] == 72000
    assert result["source"] == "kis"
    assert len(fake_cache.client.setex_calls) == 1


@pytest.mark.asyncio
async def test_get_current_price_falls_back_to_pykrx_when_kis_unavailable(monkeypatch):
    fake_cache = _FakeCache(_FakeRedisClient())

    async def _fake_get_redis_cache():
        return fake_cache

    async def _fake_fetch_kis(_stock_code):
        return None

    async def _fake_to_thread(*_args, **_kwargs):
        return {
            "stock_code": "005930",
            "stock_name": "삼성전자",
            "current_price": 70000,
            "change_rate": -1.1,
            "volume": 456,
            "timestamp": "20260219",
            "source": "pykrx",
        }

    async def _fake_wait_for(coro, **_kwargs):
        return await coro

    monkeypatch.setattr(stock_price_service.asyncio, "to_thread", _fake_to_thread)
    monkeypatch.setattr(stock_price_service.asyncio, "wait_for", _fake_wait_for)

    monkeypatch.setattr(stock_price_service, "get_redis_cache", _fake_get_redis_cache)
    monkeypatch.setattr(stock_price_service, "_fetch_price_from_kis", _fake_fetch_kis)

    result = await stock_price_service.get_current_price("005930")
    assert result["current_price"] == 70000
    assert result["source"] == "pykrx"
    assert len(fake_cache.client.setex_calls) == 1
