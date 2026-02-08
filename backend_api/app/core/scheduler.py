"""매일 08:00 KST 데이터 파이프라인 스케줄러."""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("narrative_api.scheduler")

_scheduler: AsyncIOScheduler | None = None


def _run_script(script_name: str) -> bool:
    """subprocess로 파이프라인 스크립트 실행."""
    script_path = Path(__file__).resolve().parents[2] / script_name
    if not script_path.exists():
        # Docker 환경에서는 /app/ 하위에 위치
        script_path = Path("/app") / script_name
    if not script_path.exists():
        logger.error("스크립트 없음: %s", script_name)
        return False

    logger.info("스크립트 실행 시작: %s", script_name)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=600,
            cwd=str(script_path.parent),
        )
        if result.returncode == 0:
            logger.info("스크립트 성공: %s", script_name)
            return True
        else:
            logger.error("스크립트 실패: %s\nstderr: %s", script_name, result.stderr[-500:] if result.stderr else "")
            return False
    except subprocess.TimeoutExpired:
        logger.error("스크립트 타임아웃: %s", script_name)
        return False
    except Exception as e:
        logger.error("스크립트 실행 오류: %s - %s", script_name, e)
        return False


async def run_daily_pipeline():
    """매일 실행: seed_fresh_data → generate_cases 순차 실행."""
    logger.info("=== 데일리 파이프라인 시작 ===")

    loop = asyncio.get_event_loop()

    # Step 1: 시장 데이터 수집
    ok = await loop.run_in_executor(None, _run_script, "scripts/seed_fresh_data.py")
    if not ok:
        logger.error("seed_fresh_data 실패 → 파이프라인 중단")
        return

    # Step 2: AI 케이스 생성
    await loop.run_in_executor(None, _run_script, "generate_cases.py")

    logger.info("=== 데일리 파이프라인 완료 ===")


def start_scheduler():
    """스케줄러 시작. KST 08:00 = UTC 23:00 (전날), 일-목요일."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=23, minute=0, day_of_week="sun,mon,tue,wed,thu"),
        id="daily_pipeline",
        name="Daily Data Pipeline (08:00 KST)",
        misfire_grace_time=3600,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("daily pipeline scheduled for 08:00 KST (UTC 23:00, Sun-Thu)")


def stop_scheduler():
    """스케줄러 종료."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("스케줄러 종료")
