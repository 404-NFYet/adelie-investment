"""Vision API (GPT-4o Vision) PDF extraction service."""

import base64
import io
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class VisionExtractor:
    """Service for extracting data from PDFs using Vision API."""
    
    # System prompt for financial report extraction
    SYSTEM_PROMPT = """당신은 한국 증권사 리서치 리포트 분석 전문가입니다.
주어진 PDF 페이지 이미지를 분석하여 다음 정보를 추출해주세요:

1. **기본 정보**
   - 증권사명
   - 리포트 제목
   - 작성 날짜
   - 종목명/종목코드

2. **투자 의견**
   - 투자의견 (매수/중립/매도 등)
   - 목표주가
   - 현재주가

3. **핵심 내용**
   - 핵심 투자포인트 (3-5개)
   - 주요 재무지표 (매출, 영업이익, EPS 등)
   - 리스크 요인

4. **표/그래프 데이터**
   - 표에 있는 주요 수치를 텍스트로 정리
   - 그래프의 추세와 핵심 데이터 포인트 설명

JSON 형식으로 응답해주세요."""

    def __init__(self):
        """Initialize Vision extractor."""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package is not installed. Run: pip install openai")
        
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Vision-capable model
    
    def pdf_to_images(
        self,
        pdf_data: bytes,
        dpi: int = 200,
        max_pages: int = 10,
    ) -> list[bytes]:
        """
        Convert PDF pages to images.
        
        Args:
            pdf_data: PDF file content as bytes
            dpi: Resolution for conversion (higher = better quality)
            max_pages: Maximum pages to process
            
        Returns:
            List of PNG images as bytes
        """
        if not FITZ_AVAILABLE:
            raise ImportError("PyMuPDF (fitz) is not installed. Run: pip install pymupdf")
        
        images = []
        
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        try:
            page_count = min(len(doc), max_pages)
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Calculate zoom factor for desired DPI
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes
                images.append(pix.tobytes("png"))
                
            print(f"✅ Converted {page_count} pages to images (DPI: {dpi})")
            
        finally:
            doc.close()
        
        return images
    
    def extract_from_image(
        self,
        image_data: bytes,
        page_num: int = 1,
    ) -> dict:
        """
        Extract information from a single image using Vision API.
        
        Args:
            image_data: PNG image data
            page_num: Page number for reference
            
        Returns:
            Extracted information as dictionary
        """
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode("utf-8")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"이 리서치 리포트의 {page_num}페이지를 분석해주세요.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high",  # Use high detail for financial documents
                                },
                            },
                        ],
                    },
                ],
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON from response
            import json
            try:
                # Find JSON in response
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                else:
                    json_str = content
                
                return json.loads(json_str.strip())
            except (json.JSONDecodeError, IndexError):
                # Return raw content if not JSON
                return {
                    "page": page_num,
                    "raw_content": content,
                    "parse_error": True,
                }
                
        except Exception as e:
            print(f"❌ Vision API error: {e}")
            return {
                "page": page_num,
                "error": str(e),
            }
    
    def extract_from_pdf(
        self,
        pdf_data: bytes,
        dpi: int = 200,
        max_pages: int = 5,
    ) -> dict:
        """
        Extract information from a PDF using Vision API.
        
        Args:
            pdf_data: PDF file content as bytes
            dpi: Resolution for page images
            max_pages: Maximum pages to process
            
        Returns:
            Combined extraction results
        """
        # Convert PDF to images
        images = self.pdf_to_images(pdf_data, dpi=dpi, max_pages=max_pages)
        
        # Extract from each page
        pages = []
        for i, img_data in enumerate(images):
            print(f"  Processing page {i + 1}/{len(images)}...")
            page_result = self.extract_from_image(img_data, page_num=i + 1)
            pages.append(page_result)
        
        # Combine results
        result = {
            "total_pages": len(images),
            "pages": pages,
            "summary": self._summarize_pages(pages),
        }
        
        return result
    
    def _summarize_pages(self, pages: list[dict]) -> dict:
        """Summarize extracted information from all pages."""
        # Find first valid page with basic info
        basic_info = {}
        investment_opinion = {}
        key_points = []
        financial_data = []
        
        for page in pages:
            if page.get("parse_error") or page.get("error"):
                continue
            
            # Extract basic info from first page
            if not basic_info:
                for key in ["증권사명", "리포트 제목", "작성 날짜", "종목명", "종목코드"]:
                    if key in page:
                        basic_info[key] = page[key]
            
            # Collect investment opinions
            for key in ["투자의견", "목표주가", "현재주가"]:
                if key in page and key not in investment_opinion:
                    investment_opinion[key] = page[key]
            
            # Collect key points
            if "핵심 투자포인트" in page:
                points = page["핵심 투자포인트"]
                if isinstance(points, list):
                    key_points.extend(points)
                else:
                    key_points.append(points)
            
            # Collect financial data
            if "주요 재무지표" in page:
                data = page["주요 재무지표"]
                if isinstance(data, dict):
                    financial_data.append(data)
                elif isinstance(data, list):
                    financial_data.extend(data)
        
        return {
            "basic_info": basic_info,
            "investment_opinion": investment_opinion,
            "key_points": list(set(key_points))[:5],  # Deduplicate
            "financial_data": financial_data,
        }
    
    def extract_with_direct_pdf(
        self,
        pdf_data: bytes,
    ) -> dict:
        """
        Extract information by sending PDF directly to GPT-4o.
        
        Note: This requires the model to support PDF input directly.
        As of now, Vision models work with images, not PDF files.
        This method converts the first page to high-res image.
        
        Args:
            pdf_data: PDF file content as bytes
            
        Returns:
            Extracted information
        """
        # Convert first page at high resolution
        images = self.pdf_to_images(pdf_data, dpi=300, max_pages=1)
        
        if not images:
            return {"error": "No pages extracted from PDF"}
        
        return self.extract_from_image(images[0], page_num=1)


# Singleton instance
_vision_extractor: Optional[VisionExtractor] = None


def get_vision_extractor() -> VisionExtractor:
    """Get Vision extractor instance."""
    global _vision_extractor
    if _vision_extractor is None:
        _vision_extractor = VisionExtractor()
    return _vision_extractor


# Test function
def test_vision_api():
    """Test Vision API connection."""
    try:
        extractor = get_vision_extractor()
        print("✅ Vision API initialized successfully")
        print(f"   Model: {extractor.model}")
        
        # Test with a simple API call (no image)
        response = extractor.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'Vision API Ready' in 3 words."}],
            max_tokens=10,
        )
        print(f"   Test response: {response.choices[0].message.content}")
        
        return True
    except Exception as e:
        print(f"❌ Vision API test failed: {e}")
        return False


if __name__ == "__main__":
    test_vision_api()
