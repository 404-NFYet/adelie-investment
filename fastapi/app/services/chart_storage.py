"""차트 HTML MinIO 영구 저장 서비스.

생성된 Plotly 차트 HTML을 MinIO에 세션/메시지별로 저장하고,
presigned URL로 조회할 수 있도록 한다.
"""

import logging
import time

logger = logging.getLogger("narrative_api.chart_storage")

# MinIO 서비스 lazy import
_minio_service = None
_MINIO_AVAILABLE = False

CHART_BUCKET = "extracted-data"
CHART_PREFIX = "charts"


def _get_minio():
    """MinIO 서비스 싱글톤 가져오기."""
    global _minio_service, _MINIO_AVAILABLE
    if _minio_service is not None:
        return _minio_service
    try:
        import sys
        from pathlib import Path
        pipeline_path = str(Path(__file__).resolve().parent.parent.parent.parent / "datapipeline")
        if pipeline_path not in sys.path:
            sys.path.insert(0, pipeline_path)
        from services.minio_service import get_minio_service
        _minio_service = get_minio_service()
        _MINIO_AVAILABLE = True
        return _minio_service
    except Exception as e:
        logger.debug("MinIO 서비스 초기화 실패: %s", e)
        _MINIO_AVAILABLE = False
        return None


def save_chart_html(session_id: str, html_content: str) -> str | None:
    """차트 HTML을 MinIO에 저장하고 오브젝트 경로를 반환.

    Args:
        session_id: 튜터 세션 UUID
        html_content: Plotly 차트 HTML 문자열

    Returns:
        MinIO 오브젝트 경로 (예: charts/{session_id}/{timestamp}.html) 또는 None
    """
    minio = _get_minio()
    if not minio:
        return None

    try:
        object_path = f"{CHART_PREFIX}/{session_id}/{int(time.time())}.html"
        minio.upload_bytes(
            data=html_content.encode("utf-8"),
            object_name=object_path,
            bucket=CHART_BUCKET,
            content_type="text/html",
        )
        logger.info("차트 MinIO 저장: %s", object_path)
        return object_path
    except Exception as e:
        logger.debug("MinIO 차트 저장 실패: %s", e)
        return None


def get_chart_presigned_url(minio_path: str, expires: int = 3600) -> str | None:
    """MinIO 차트의 presigned URL을 생성.

    Args:
        minio_path: MinIO 오브젝트 경로
        expires: URL 유효 시간 (초)

    Returns:
        presigned URL 또는 None
    """
    minio = _get_minio()
    if not minio:
        return None

    try:
        return minio.get_presigned_url(
            minio_path, bucket=CHART_BUCKET, expires=expires,
        )
    except Exception as e:
        logger.debug("presigned URL 생성 실패: %s", e)
        return None
