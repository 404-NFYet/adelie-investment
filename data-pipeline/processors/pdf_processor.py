"""
Vision LLM을 사용한 PDF 처리 모듈
- PDF -> 이미지 변환 (고해상도)
- GPT-4o Vision으로 텍스트/표/차트 추출
"""

import asyncio
import base64
import io
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from openai import AsyncOpenAI
from PIL import Image

logger = logging.getLogger(__name__)

# 기본 설정
DEFAULT_DPI = 200  # 고해상도 변환
MAX_IMAGE_SIZE = (2048, 2048)  # Vision API 권장 최대 크기


@dataclass
class ExtractedPage:
    """추출된 페이지 데이터"""
    page_num: int
    text: str
    tables: list[dict]
    charts: list[dict]
    summary: str
    
    def to_dict(self) -> dict:
        return {
            "page_num": self.page_num,
            "text": self.text,
            "tables": self.tables,
            "charts": self.charts,
            "summary": self.summary
        }


def pdf_to_images(
    pdf_path: str,
    dpi: int = DEFAULT_DPI,
    max_pages: Optional[int] = None
) -> list[Image.Image]:
    """
    PDF를 고해상도 이미지로 변환
    
    Args:
        pdf_path: PDF 파일 경로
        dpi: 해상도 (기본: 200)
        max_pages: 최대 페이지 수 (선택)
        
    Returns:
        list[Image.Image]: PIL 이미지 리스트
    """
    images = []
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        logger.info(f"Converting {total_pages} pages from {pdf_path}")
        
        # DPI에 따른 zoom 계산 (72 DPI 기준)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        
        for page_num in range(total_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            
            # PIL Image로 변환
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 크기 조정 (필요시)
            if img.width > MAX_IMAGE_SIZE[0] or img.height > MAX_IMAGE_SIZE[1]:
                img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            
            images.append(img)
            logger.debug(f"Converted page {page_num + 1}/{total_pages}")
        
        doc.close()
        logger.info(f"Converted {len(images)} pages to images")
        
    except Exception as e:
        logger.error(f"Failed to convert PDF to images: {e}")
        raise
    
    return images


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """
    PIL Image를 base64 문자열로 변환
    
    Args:
        image: PIL Image
        format: 이미지 포맷
        
    Returns:
        str: base64 인코딩된 문자열
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


async def extract_with_vision(
    image: Image.Image,
    page_num: int,
    client: AsyncOpenAI,
    model: str = "gpt-4o"
) -> ExtractedPage:
    """
    GPT-4o Vision으로 페이지 내용 추출
    
    Args:
        image: 페이지 이미지
        page_num: 페이지 번호
        client: OpenAI 클라이언트
        model: 모델명
        
    Returns:
        ExtractedPage: 추출된 내용
    """
    base64_image = image_to_base64(image)
    
    prompt = """이 리서치 리포트 페이지를 분석해주세요.

다음 정보를 JSON 형식으로 추출해주세요:
1. text: 페이지의 주요 텍스트 내용 (마크다운 형식)
2. tables: 표가 있다면 각 표의 내용 (리스트 형식)
3. charts: 차트/그래프가 있다면 설명 (리스트 형식)
4. summary: 이 페이지의 핵심 내용 요약 (2-3문장)

반드시 다음 JSON 형식으로 응답해주세요:
{
    "text": "...",
    "tables": [{"title": "...", "data": [...]}],
    "charts": [{"type": "...", "description": "..."}],
    "summary": "..."
}"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        
        # JSON 파싱
        import json
        data = json.loads(result)
        
        return ExtractedPage(
            page_num=page_num,
            text=data.get("text", ""),
            tables=data.get("tables", []),
            charts=data.get("charts", []),
            summary=data.get("summary", "")
        )
        
    except Exception as e:
        logger.error(f"Failed to extract page {page_num}: {e}")
        return ExtractedPage(
            page_num=page_num,
            text="",
            tables=[],
            charts=[],
            summary=f"Extraction failed: {str(e)}"
        )


async def process_pdf(
    pdf_path: str,
    max_pages: Optional[int] = None,
    dpi: int = DEFAULT_DPI,
    model: str = "gpt-4o",
    concurrent_limit: int = 3
) -> dict:
    """
    PDF 전체 처리 메인 함수
    
    Args:
        pdf_path: PDF 파일 경로
        max_pages: 최대 처리 페이지 수
        dpi: 이미지 해상도
        model: Vision 모델
        concurrent_limit: 동시 처리 수
        
    Returns:
        dict: 추출 결과
    """
    # OpenAI 클라이언트 초기화
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    client = AsyncOpenAI(api_key=api_key)
    
    # PDF -> 이미지 변환
    images = pdf_to_images(pdf_path, dpi=dpi, max_pages=max_pages)
    
    if not images:
        return {"error": "No pages extracted", "pages": []}
    
    # 세마포어로 동시 처리 제한
    semaphore = asyncio.Semaphore(concurrent_limit)
    
    async def process_page(idx: int, img: Image.Image) -> ExtractedPage:
        async with semaphore:
            logger.info(f"Processing page {idx + 1}/{len(images)}")
            return await extract_with_vision(img, idx + 1, client, model)
    
    # 병렬 처리
    tasks = [process_page(i, img) for i, img in enumerate(images)]
    results = await asyncio.gather(*tasks)
    
    # 전체 요약 생성
    all_summaries = [r.summary for r in results if r.summary]
    
    return {
        "file": os.path.basename(pdf_path),
        "total_pages": len(images),
        "pages": [r.to_dict() for r in results],
        "combined_summary": " ".join(all_summaries)
    }


def save_images(
    images: list[Image.Image],
    output_dir: str,
    prefix: str = "page"
) -> list[str]:
    """
    이미지들을 파일로 저장
    
    Args:
        images: PIL Image 리스트
        output_dir: 출력 디렉토리
        prefix: 파일명 접두사
        
    Returns:
        list[str]: 저장된 파일 경로 리스트
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    saved_paths = []
    for i, img in enumerate(images):
        path = os.path.join(output_dir, f"{prefix}_{i+1:03d}.png")
        img.save(path, "PNG")
        saved_paths.append(path)
        logger.debug(f"Saved {path}")
    
    logger.info(f"Saved {len(saved_paths)} images to {output_dir}")
    return saved_paths


if __name__ == "__main__":
    # 테스트
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        if len(sys.argv) < 2:
            print("Usage: python pdf_processor.py <pdf_path>")
            return
        
        pdf_path = sys.argv[1]
        
        # PDF -> 이미지 변환만 테스트
        print(f"Converting {pdf_path} to images...")
        images = pdf_to_images(pdf_path, max_pages=3)
        print(f"Converted {len(images)} pages")
        
        # 이미지 저장
        save_images(images, "./output_images", prefix="test")
        
        # Vision API 테스트 (API 키 필요)
        if os.getenv("OPENAI_API_KEY"):
            print("\nProcessing with Vision API...")
            result = await process_pdf(pdf_path, max_pages=2)
            print(f"Processed {result['total_pages']} pages")
            print(f"Combined summary: {result['combined_summary'][:200]}...")
    
    asyncio.run(main())
