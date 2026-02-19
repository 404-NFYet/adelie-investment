"""퀴즈 보상 API - /api/v1/quiz/*"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.portfolio import UserPortfolio
from app.models.reward import BriefingReward
from app.services.portfolio_service import get_or_create_portfolio

router = APIRouter(prefix="/quiz", tags=["quiz"])

CORRECT_REWARD = 100_000  # 정답: 10만원
INCORRECT_REWARD = 10_000  # 오답: 1만원


class QuizRewardRequest(BaseModel):
    scenario_id: str
    selected_answer: int
    correct_answer: int


class QuizRewardResponse(BaseModel):
    reward_amount: int
    is_correct: bool
    new_cash_balance: float


@router.post("/reward", response_model=QuizRewardResponse)
async def process_quiz_reward(
    req: QuizRewardRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """퀴즈 보상 처리 - 정답 10만원, 오답 1만원"""
    user_id = current_user["id"]
    is_correct = req.selected_answer == req.correct_answer
    reward_amount = CORRECT_REWARD if is_correct else INCORRECT_REWARD

    # 포트폴리오 조회 (없으면 자동 생성, 중복 안전)
    portfolio = await get_or_create_portfolio(db, user_id)

    # 포트폴리오 현금 추가 + 누적 보상액 갱신 (특정 portfolio.id로 1건만 업데이트)
    new_cash = portfolio.current_cash + reward_amount
    await db.execute(
        update(UserPortfolio)
        .where(UserPortfolio.id == portfolio.id)
        .values(
            current_cash=new_cash,
            total_rewards_received=UserPortfolio.total_rewards_received + reward_amount,
        )
    )

    # 보상 기록 (BriefingReward 필수 컬럼 포함)
    reward = BriefingReward(
        user_id=user_id,
        portfolio_id=portfolio.id,
        case_id=0,
        base_reward=reward_amount,
        multiplier=1.0,
        final_reward=reward_amount,
        quiz_correct=is_correct,
        status="completed",
        maturity_at=datetime.utcnow() + timedelta(days=7),
        applied_at=datetime.utcnow(),
    )
    db.add(reward)
    await db.commit()

    return QuizRewardResponse(
        reward_amount=reward_amount,
        is_correct=is_correct,
        new_cash_balance=new_cash,
    )
