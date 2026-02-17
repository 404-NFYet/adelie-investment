"""Portfolio, trading, and reward schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- Portfolio ---

class HoldingResponse(BaseModel):
    """보유 종목 정보 (실시간 평가 포함)."""
    stock_code: str
    stock_name: str
    quantity: int
    avg_buy_price: float
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_pct: Optional[float] = None


class PortfolioResponse(BaseModel):
    """포트폴리오 전체 정보."""
    id: int
    portfolio_name: str
    initial_cash: int
    current_cash: int
    total_rewards_received: int = 0
    holdings: list[HoldingResponse] = []
    total_value: float = 0
    total_profit_loss: float = 0
    total_profit_loss_pct: float = 0


class PortfolioSummary(BaseModel):
    """경량 포트폴리오 요약 (BottomNav 뱃지용)."""
    total_value: int
    total_profit_loss: int
    total_profit_loss_pct: float


# --- Trading ---

class TradeRequest(BaseModel):
    """매수/매도 요청."""
    stock_code: str
    stock_name: str
    trade_type: Literal["buy", "sell"]
    quantity: int = Field(gt=0)
    trade_reason: Optional[str] = None
    case_id: Optional[int] = None


class TradeResponse(BaseModel):
    """거래 결과."""
    id: int
    trade_type: str
    stock_code: str
    stock_name: str
    quantity: int
    price: float
    total_amount: float
    trade_reason: Optional[str] = None
    traded_at: datetime
    remaining_cash: int


class TradeHistoryResponse(BaseModel):
    """거래 내역 목록."""
    trades: list[TradeResponse]
    total_count: int


# --- Stock Price ---

class StockPriceResponse(BaseModel):
    """종목 현재가."""
    stock_code: str
    stock_name: str
    current_price: int
    change_rate: float
    volume: int
    timestamp: str


class BatchStockPriceResponse(BaseModel):
    """복수 종목 현재가."""
    prices: list[StockPriceResponse]
    date: str


# --- Reward ---

class BriefingCompleteRequest(BaseModel):
    """브리핑 완료 보상 요청."""
    case_id: int


class RewardResponse(BaseModel):
    """보상 지급 결과."""
    reward_id: int
    base_reward: int
    status: str
    maturity_at: datetime
    message: str


class RewardItem(BaseModel):
    """개별 보상 정보."""
    reward_id: int
    case_id: int
    base_reward: int
    multiplier: float
    final_reward: int
    status: str
    maturity_at: str


class RewardsListResponse(BaseModel):
    """보상 목록."""
    rewards: list[RewardItem]


# --- Leaderboard ---

class LeaderboardEntry(BaseModel):
    """리더보드 항목."""
    rank: int
    user_id: int
    username: str
    total_value: float
    profit_loss: float
    profit_loss_pct: float
    is_me: bool = False


class LeaderboardResponse(BaseModel):
    """리더보드 응답."""
    my_rank: Optional[int] = None
    my_entry: Optional[LeaderboardEntry] = None
    rankings: list[LeaderboardEntry]
    total_users: int
