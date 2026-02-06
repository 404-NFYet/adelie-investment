"""Historical case search tool using Perplexity API."""

import os
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@tool
def search_historical_cases(
    query: str,
    recency: str = "year",
    limit: int = 3,
) -> str:
    """
    역사적 주식시장 사례를 검색합니다. Perplexity API를 사용하여 한국 주식시장의 과거 사례를 찾습니다.
    
    Args:
        query: 검색 쿼리 (예: "반도체 호황", "금리 인상 영향")
        recency: 검색 기간 (year/month/week)
        limit: 결과 개수
        
    Returns:
        검색 결과 (JSON 형식)
    """
    import json
    from openai import OpenAI
    
    api_key = os.getenv("PERPLEXITY_API_KEY", "")
    if not api_key:
        return json.dumps({"error": "PERPLEXITY_API_KEY not set"}, ensure_ascii=False)
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai"
    )
    
    search_query = f"한국 주식시장 역사적 사례 {query}"
    
    system_prompt = """당신은 한국 주식시장 역사 전문가입니다.
사용자의 질문에 대해 관련된 과거 한국 주식시장 사례를 찾아 JSON 형식으로 응답해주세요.

응답 형식:
```json
{
    "cases": [
        {
            "title": "사례 제목",
            "year": 연도,
            "summary": "사례 요약 (100자 이내)",
            "keywords": ["키워드1", "키워드2"],
            "impact": "시장 영향"
        }
    ],
    "search_summary": "검색 결과 요약"
}
```
"""
    
    try:
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": search_query},
            ],
            max_tokens=1500,
        )
        
        content = response.choices[0].message.content
        
        # Try to extract JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content
        
        try:
            result = json.loads(json_str.strip())
            # Limit results
            if "cases" in result:
                result["cases"] = result["cases"][:limit]
            return json.dumps(result, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return json.dumps({
                "search_summary": content,
                "cases": [],
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "cases": [],
        }, ensure_ascii=False, indent=2)
