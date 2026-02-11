"""매일 08:00 KST 데이터 파이프라인 스케줄러."""

import asyncio
import logging
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("narrative_api.scheduler")

_scheduler: AsyncIOScheduler | None = None


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


async def run_daily_pipeline():
    """매일 실행: LangGraph 통합 파이프라인 (keywords + narratives)."""
    logger.info("=== 데일리 파이프라인 시작 ===")

    # LangGraph 통합 파이프라인 (keyword + narrative 생성 통합)
    ok = await _run_script("keyword_pipeline_graph.py")
    if not ok:
        logger.error("LangGraph 파이프라인 실패 → 파이프라인 중단")
        return

    logger.info("=== 데일리 파이프라인 완료 ===")


def start_scheduler():
    """스케줄러 시작. KST 16:10 = UTC 07:10, 월-금요일 (장 마감 후 30분)."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_daily_pipeline,
        trigger=CronTrigger(hour=7, minute=10, day_of_week="mon,tue,wed,thu,fri"),
        id="daily_pipeline",
        name="Daily Data Pipeline (16:10 KST)",
        misfire_grace_time=3600,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("daily pipeline scheduled for 16:10 KST (UTC 07:10, Mon-Fri)")


def stop_scheduler():
    """스케줄러 종료."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("스케줄러 종료")
