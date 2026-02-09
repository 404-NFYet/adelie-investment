"""Quiz Reward API - 퀴즈 보상 처리."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.reward import BriefingReward
from app.models.portfolio import UserPortfolio

router = APIRouter(prefix="/quiz", tags=["Quiz"])

CORRECT_REWARD = 100_000  # 10만원
INCORRECT_REWARD = 10_000  # 1만원


class QuizRewardRequest(BaseModel):
    user_id: int
    scenario_id: str
    selected_answer: str
    correct_answer: str


class QuizRewardResponse(BaseModel):
    reward_amount: int
    is_correct: bool
    new_cash_balance: int


@router.post("/reward", response_model=QuizRewardResponse)
async def process_quiz_reward(request: QuizRewardRequest, db: AsyncSession = Depends(get_db)):
    """퀴즈 보상 처리 - 정답 10만원, 오답 1만원."""
    
    # 포트폴리오 조회
    stmt = select(UserPortfolio).where(UserPortfolio.user_id == request.user_id)
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # 정답 여부 확인
    is_correct = request.selected_answer == request.correct_answer
    reward_amount = CORRECT_REWARD if is_correct else INCORRECT_REWARD
    
    # 포트폴리오 현금 업데이트
    portfolio.current_cash += reward_amount
    portfolio.updated_at = datetime.utcnow()
    
    # 보상 기록 생성
    reward = BriefingReward(
        user_id=request.user_id,
        portfolio_id=portfolio.id,
        case_id=0,
        quiz_correct=is_correct,
        base_reward=reward_amount,
        multiplier=1.0,
        final_reward=reward_amount,
        status="applied",
        maturity_at=datetime.utcnow() + timedelta(days=7),
        applied_at=datetime.utcnow(),
    )
    db.add(reward)
    
    await db.commit()
    
    return QuizRewardResponse(
        reward_amount=reward_amount,
        is_correct=is_correct,
        new_cash_balance=portfolio.current_cash,
    )
