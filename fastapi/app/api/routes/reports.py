"""증권사 리포트 API 라우트 - /api/v1/reports/*"""

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.report import BrokerReport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Broker Reports"])


# ── Schemas ──


class BrokerReportResponse(BaseModel):
    """증권사 리포트 응답."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    broker_name: str
    report_title: str
    report_date: date
    stock_codes: Optional[list] = None
    pdf_url: Optional[str] = None
    minio_path: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None


class BrokerReportDetailResponse(BrokerReportResponse):
    """증권사 리포트 상세 응답 (extracted_text 포함)."""
    extracted_text: Optional[str] = None


# ── API 엔드포인트 ──


@router.get("")
async def list_reports(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=50, description="페이지 크기 (최대 50)"),
    broker_name: Optional[str] = Query(None, description="증권사명 필터"),
    start_date: Optional[date] = Query(None, description="시작일 필터 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="종료일 필터 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
):
    """리포트 목록 조회 (페이지네이션 + 증권사/날짜 필터).

    report_date 기준 최신순으로 정렬한다.
    """
    # 기본 쿼리 조건 구성
    conditions = []
    if broker_name:
        conditions.append(BrokerReport.broker_name == broker_name)
    if start_date:
        conditions.append(BrokerReport.report_date >= start_date)
    if end_date:
        conditions.append(BrokerReport.report_date <= end_date)

    # 총 건수 쿼리
    count_stmt = select(func.count(BrokerReport.id))
    for cond in conditions:
        count_stmt = count_stmt.where(cond)

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # 목록 쿼리 (페이지네이션)
    offset = (page - 1) * size
    list_stmt = (
        select(BrokerReport)
        .order_by(desc(BrokerReport.report_date))
        .offset(offset)
        .limit(size)
    )
    for cond in conditions:
        list_stmt = list_stmt.where(cond)

    result = await db.execute(list_stmt)
    reports = result.scalars().all()

    data = [
        {
            "id": r.id,
            "broker_name": r.broker_name,
            "report_title": r.report_title,
            "report_date": r.report_date.isoformat(),
            "stock_codes": r.stock_codes,
            "pdf_url": r.pdf_url,
            "minio_path": r.minio_path,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]

    return {"status": "success", "data": data, "total": total}


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """리포트 상세 조회.

    extracted_text를 포함한 전체 리포트 정보를 반환한다.
    """
    result = await db.execute(
        select(BrokerReport).where(BrokerReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다")

    data = {
        "id": report.id,
        "broker_name": report.broker_name,
        "report_title": report.report_title,
        "report_date": report.report_date.isoformat(),
        "stock_codes": report.stock_codes,
        "pdf_url": report.pdf_url,
        "minio_path": report.minio_path,
        "extracted_text": report.extracted_text,
        "summary": report.summary,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }

    return {"status": "success", "data": data}


@router.get("/stock/{stock_code}")
async def get_reports_by_stock(
    stock_code: str,
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=50, description="페이지 크기 (최대 50)"),
    db: AsyncSession = Depends(get_db),
):
    """종목별 리포트 조회.

    stock_codes JSONB 배열에서 해당 종목 코드를 포함하는 리포트를 검색한다.
    PostgreSQL JSONB contains 연산자(@>)를 사용한다.
    """
    # JSONB contains 조건: stock_codes @> '["종목코드"]'
    jsonb_condition = BrokerReport.stock_codes.op("@>")(f'["{stock_code}"]')

    # 총 건수 쿼리
    count_stmt = select(func.count(BrokerReport.id)).where(jsonb_condition)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # 목록 쿼리 (페이지네이션)
    offset = (page - 1) * size
    list_stmt = (
        select(BrokerReport)
        .where(jsonb_condition)
        .order_by(desc(BrokerReport.report_date))
        .offset(offset)
        .limit(size)
    )

    result = await db.execute(list_stmt)
    reports = result.scalars().all()

    data = [
        {
            "id": r.id,
            "broker_name": r.broker_name,
            "report_title": r.report_title,
            "report_date": r.report_date.isoformat(),
            "stock_codes": r.stock_codes,
            "pdf_url": r.pdf_url,
            "minio_path": r.minio_path,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]

    return {"status": "success", "data": data, "total": total}
