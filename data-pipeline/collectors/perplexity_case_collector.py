"""
# [2026-02-06] Perplexity API를 사용한 역사적 사례 수집
현재 이슈와 유사한 과거 한국 주식 사례를 검색하여 수집합니다.
"""

import os
import json
from typing import Optional
import httpx

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL = "sonar-pro"  # Korean context를 위해 sonar-pro 사용


class PerplexityCaseCollector:
    """Perplexity API를 사용한 역사적 사례 수집기."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai"
        
    def _build_search_query(self, topic: str, context: str = "") -> str:
        """한국 주식 역사적 사례 검색 쿼리 생성."""
        base_query = f"""한국 주식시장에서 "{topic}"과 유사한 과거 역사적 사례를 찾아주세요.

검색 조건:
- 한국 KOSPI/KOSDAQ 시장 중심
- 2000년 이후 실제 사례
- 비슷한 패턴이나 상황이 있었던 과거 이벤트
- 당시 시장 상황과 주요 종목 반응

{context}

다음 형식으로 정리해주세요:
1. 사례 제목
2. 발생 시기
3. 배경 및 상황
4. 관련 종목 및 시장 반응
5. 현재와의 유사점/차이점"""
        return base_query
    
    async def search_historical_case(
        self,
        topic: str,
        context: str = "",
        max_tokens: int = 2000,
    ) -> dict:
        """역사적 사례 검색."""
        if not self.api_key:
            return {
                "success": False,
                "error": "Perplexity API key not configured",
            }
        
        query = self._build_search_query(topic, context)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": PERPLEXITY_MODEL,
                        "messages": [
                            {
                                "role": "system",
                                "content": "당신은 한국 주식시장 역사 전문가입니다. 과거 사례를 정확하고 객관적으로 분석합니다."
                            },
                            {
                                "role": "user",
                                "content": query,
                            }
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                        "return_citations": True,
                        "return_related_questions": True,
                    },
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API error: {response.status_code}",
                        "detail": response.text,
                    }
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = data.get("citations", [])
                related_questions = data.get("related_questions", [])
                
                return {
                    "success": True,
                    "topic": topic,
                    "content": content,
                    "citations": citations,
                    "related_questions": related_questions,
                    "model": PERPLEXITY_MODEL,
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }
    
    async def batch_search_cases(
        self,
        topics: list[dict],
        save_path: Optional[str] = None,
    ) -> list[dict]:
        """여러 토픽에 대한 역사적 사례 배치 검색."""
        results = []
        
        for topic_info in topics:
            topic = topic_info.get("topic", "")
            context = topic_info.get("context", "")
            
            print(f"  Searching: {topic[:50]}...")
            
            result = await self.search_historical_case(topic, context)
            result["topic_info"] = topic_info
            results.append(result)
        
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"  Saved results to {save_path}")
        
        return results


async def collect_historical_cases(
    topics: list[dict],
    save_path: Optional[str] = None,
) -> list[dict]:
    """역사적 사례 수집 편의 함수."""
    collector = PerplexityCaseCollector()
    return await collector.batch_search_cases(topics, save_path)


# CLI 테스트용
if __name__ == "__main__":
    import asyncio
    
    test_topics = [
        {
            "topic": "AI 반도체 거품론",
            "context": "엔비디아 중심 AI 반도체 급등과 닷컴 버블 비교",
        },
        {
            "topic": "금리 인상과 성장주 조정",
            "context": "2022년 금리 인상기와 과거 사례 비교",
        },
    ]
    
    async def main():
        results = await collect_historical_cases(test_topics)
        for r in results:
            print(f"\n{'='*50}")
            print(f"Topic: {r.get('topic', 'N/A')}")
            print(f"Success: {r.get('success', False)}")
            if r.get("success"):
                print(f"Content length: {len(r.get('content', ''))}")
                print(f"Citations: {len(r.get('citations', []))}")
    
    asyncio.run(main())
