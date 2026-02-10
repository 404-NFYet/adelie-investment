"""PDF 텍스트 추출기.

pdfplumber를 사용하여 증권사 리포트 PDF에서 텍스트를 추출한다.
URL에서 직접 다운로드하거나, 로컬 파일에서 추출 가능.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

LOGGER = logging.getLogger(__name__)


@dataclass
class ExtractedPDF:
    """PDF 추출 결과."""

    source: str          # URL 또는 파일 경로
    text: str            # 추출된 전체 텍스트
    page_count: int = 0
    char_count: int = 0


class PDFExtractor:
    """PDF 텍스트 추출기."""

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    async def extract_from_url(self, url: str) -> ExtractedPDF:
        """URL에서 PDF를 다운로드하고 텍스트를 추출.

        Args:
            url: PDF 파일 URL

        Returns:
            ExtractedPDF 결과
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                pdf_bytes = resp.content

            return self._extract_text(pdf_bytes, source=url)

        except httpx.HTTPStatusError as exc:
            LOGGER.warning("PDF 다운로드 실패: %s (status=%d)", url, exc.response.status_code)
            return ExtractedPDF(source=url, text="", page_count=0, char_count=0)
        except Exception as exc:
            LOGGER.error("PDF 추출 실패: %s - %s", url, exc)
            return ExtractedPDF(source=url, text="", page_count=0, char_count=0)

    def extract_from_file(self, filepath: str | Path) -> ExtractedPDF:
        """로컬 파일에서 텍스트 추출.

        Args:
            filepath: PDF 파일 경로

        Returns:
            ExtractedPDF 결과
        """
        path = Path(filepath)
        if not path.exists():
            LOGGER.warning("파일 없음: %s", filepath)
            return ExtractedPDF(source=str(filepath), text="", page_count=0, char_count=0)

        try:
            pdf_bytes = path.read_bytes()
            return self._extract_text(pdf_bytes, source=str(filepath))
        except Exception as exc:
            LOGGER.error("PDF 파일 추출 실패: %s - %s", filepath, exc)
            return ExtractedPDF(source=str(filepath), text="", page_count=0, char_count=0)

    @staticmethod
    def _extract_text(pdf_bytes: bytes, source: str) -> ExtractedPDF:
        """PDF 바이트에서 텍스트 추출."""
        try:
            import pdfplumber
        except ImportError:
            LOGGER.error("pdfplumber가 설치되지 않았습니다: pip install pdfplumber")
            return ExtractedPDF(source=source, text="", page_count=0, char_count=0)

        pages_text: list[str] = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text.strip())

            full_text = "\n\n".join(pages_text)
            LOGGER.info("PDF 추출 완료: %s (%d페이지, %d자)", source, page_count, len(full_text))

            return ExtractedPDF(
                source=source,
                text=full_text,
                page_count=page_count,
                char_count=len(full_text),
            )
        except Exception as exc:
            LOGGER.error("PDF 텍스트 추출 실패: %s - %s", source, exc)
            return ExtractedPDF(source=source, text="", page_count=0, char_count=0)

    async def extract_batch(self, urls: list[str]) -> list[ExtractedPDF]:
        """여러 PDF를 병렬로 다운로드 및 추출.

        Args:
            urls: PDF URL 목록

        Returns:
            ExtractedPDF 결과 목록
        """
        import asyncio

        tasks = [self.extract_from_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        extracted: list[ExtractedPDF] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                LOGGER.error("배치 PDF 추출 실패 [%d]: %s", i, result)
                extracted.append(ExtractedPDF(source=urls[i], text="", page_count=0, char_count=0))
            else:
                extracted.append(result)

        LOGGER.info("배치 PDF 추출: %d/%d 성공", sum(1 for e in extracted if e.text), len(urls))
        return extracted
