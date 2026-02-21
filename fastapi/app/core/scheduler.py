"""매일 KST 09:00 모닝 파이프라인 + KST 16:10 레거시 파이프라인 스케줄러."""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
DISCORD_WEBHOOK = os.getenv("DISCORD_PIPELINE_WEBHOOK", "")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("narrative_api.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def _notify_discord(title: str, message: str, color: int = 15158332) -> None:
    """Discord webhook으로 임베드 알림 전송."""
    if not DISCORD_WEBHOOK:
        return
    import httpx
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": color,
        }]
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(DISCORD_WEBHOOK, json=payload)
    except Exception as e:
        logger.warning("Discord 알림 전송 실패: %s", e)


async def _is_trading_day() -> bool:
    """오늘이 한국 주식시장 영업일인지 확인."""
    today_str = datetime.now(KST).strftime("%Y%m%d")
    try:
        from app.services.market_calendar import is_kr_market_open_today
        result = await is_kr_market_open_today()
        logger.info("영업일 체크: %s → %s", today_str, "영업일" if result else "휴장일")
        return result
    except Exception as e:
        logger.warning("영업일 확인 실패 (실행 진행): %s", e)
        return True  # 실패 시 실행


async def _run_datapipeline_subprocess() -> bool:
    """datapipeline.run을 subprocess로 실행 (60분 타임아웃)."""
    # Docker: /app, 로컬: 프로젝트 루트
    cwd = Path("/app") if Path("/app/datapipeline").exists() else Path(__file__).resolve().parents[3]
    logger.info("datapipeline subprocess 시작 (cwd=%s)", cwd)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "datapipeline.run",
            "--backend", "live", "--market", "KR", "--topic-count", "3",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("datapipeline 타임아웃 (60분)")
            return False

        if proc.returncode == 0:
            logger.info("datapipeline 완료")
            return True
        else:
            stderr_text = stderr.decode() if stderr else ""
            logger.error("datapipeline 실패\nstderr: %s", stderr_text[-500:] if stderr_text else "")
            return False
    except Exception as e:
        logger.error("datapipeline 실행 오류: %s", e)
        return False


async def _run_script(script_name: str) -> bool:
    """asyncio subprocess로 파이프라인 스크립트 비동기 실행."""
    # scripts/ 디렉토리에서 먼저 찾기
    script_path = Path(__file__).resolve().parents[2] / "scripts" / script_name
    if not script_path.exists():
        # Docker 환경에서는 /app/scripts/ 하위에 위치
        script_path = Path("/app/scripts") / script_name
    if not script_path.exists():
        logger.error("스크립트 없음: %s", script_name)
        return False

    logger.info("스크립트 실행 시작: %s", script_name)
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("스크립트 타임아웃: %s", script_name)
            return False

        if proc.returncode == 0:
            logger.info("스크립트 성공: %s", script_name)
            return True
        else:
            stderr_text = stderr.decode() if stderr else ""
            logger.error(
                "스크립트 실패: %s\nstderr: %s",
                script_name,
                stderr_text[-500:] if stderr_text else "",
            )
            return False
    except Exception as e:
        logger.error("스크립트 실행 오류: %s - %s", script_name, e)
        return False


async def run_morning_pipeline():
    """모닝 파이프라인: KST 09:00, 영업일만 실행."""
    if not await _is_trading_day():
        logger.info("=== 모닝 파이프라인 스킵 (휴장일) ===")
        return

    logger.info("=== 모닝 파이프라인 시작 ===")
    ok = await _run_datapipeline_subprocess()

    if ok:
        await _post_pipeline_hooks()
        today = datetime.now(KST).strftime("%Y-%m-%d")
        await _notify_discord(
            f"✅ 모닝 파이프라인 완료 ({today})",
            "오늘의 브리핑 데이터가 생성됐습니다.",
            color=3066993,  # 초록
        )
    else:
        logger.error("모닝 파이프라인 실패")
        await _notify_discord(
            "❌ 모닝 파이프라인 실패",
            f"날짜: {datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')}\n"
            "수동 실행: `POST /api/v1/pipeline/run?force=true`",
            color=15158332,  # 빨강
        )
    logger.info("=== 모닝 파이프라인 완료 ===")


async def run_daily_pipeline():
    """매일 실행: LangGraph 통합 파이프라인 (keywords + narratives). 휴장일 스킵."""
    if not await _is_trading_day():
        logger.info("=== 데일리 파이프라인 스킵 (휴장일) ===")
        return

    logger.info("=== 데일리 파이프라인 시작 ===")

    # LangGraph 통합 파이프라인 (keyword + narrative 생성 통합)
    ok = await _run_script("keyword_pipeline_graph.py")
    if not ok:
        logger.error("LangGraph 파이프라인 실패 → 파이프라인 중단")
        return

    # ── 후처리: 캐시 무효화 + MV 리프레시 ──
    await _post_pipeline_hooks()

    logger.info("=== 데일리 파이프라인 완료 ===")


async def _post_pipeline_hooks():
    """파이프라인 완료 후 캐시 무효화 및 MV 갱신."""
    from app.services.redis_cache import get_redis_cache
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text

    # 1. Redis 캐시 무효화
    try:
        cache = await get_redis_cache()
        deleted = await cache.invalidate_pipeline_caches()
        logger.info(f"Redis 캐시 무효화: {deleted}개 키")
    except Exception as e:
        logger.warning(f"캐시 무효화 실패 (서비스 영향 없음): {e}")

    # 2. Materialized View 리프레시
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text(
                "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_keyword_frequency"
            ))
            await session.commit()
        logger.info("mv_keyword_frequency 리프레시 완료")
    except Exception as e:
        logger.warning(f"MV 리프레시 실패 (다음 파이프라인에서 재시도): {e}")


def start_scheduler():
    """스케줄러 시작. 모닝(KST 09:00) + 데일리(KST 16:10), 월-금."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()

    # 모닝 파이프라인: KST 09:00 = UTC 00:00
    _scheduler.add_job(
        run_morning_pipeline,
        trigger=CronTrigger(hour=0, minute=0, day_of_week="mon,tue,wed,thu,fri"),
        id="morning_pipeline",
        name="Morning Data Pipeline (09:00 KST)",
        misfire_grace_time=3600,
        replace_existing=True,
    )

    # 레거시 데일리 파이프라인: KST 16:10 = UTC 07:10
    _scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=7, minute=10, day_of_week="mon,tue,wed,thu,fri"),
        id="daily_pipeline",
        name="Daily Data Pipeline (16:10 KST)",
        misfire_grace_time=3600,
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("스케줄러 시작: 모닝(09:00 KST) + 데일리(16:10 KST), Mon-Fri")


def stop_scheduler():
    """스케줄러 종료."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("스케줄러 종료")
