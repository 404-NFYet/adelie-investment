"""Past-present comparison tool."""

import os
from pathlib import Path

from langchain_core.tools import tool

from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@tool
def compare_past_present(
    past_event: str,
    current_situation: str,
) -> str:
    """
    과거 사례와 현재 상황을 비교 분석합니다.
    
    Args:
        past_event: 과거 사례 설명 (예: "2008년 금융위기")
        current_situation: 현재 상황 설명 (예: "2024년 금리 인상기")
        
    Returns:
        비교 분석 결과 (JSON 형식)
    """
    import json
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return json.dumps({"error": "OPENAI_API_KEY not set"}, ensure_ascii=False)
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = """당신은 한국 주식시장 분석 전문가입니다.
과거 사례와 현재 상황을 비교 분석하여 다음 JSON 형식으로 응답해주세요:

```json
{
    "past_event": {
        "title": "과거 사례 제목",
        "period": "시기",
        "key_factors": ["요인1", "요인2"],
        "market_impact": "시장 영향"
    },
    "current_situation": {
        "title": "현재 상황 제목",
        "key_factors": ["요인1", "요인2"],
        "market_outlook": "시장 전망"
    },
    "comparison_points": [
        {
            "aspect": "비교 관점",
            "past": "과거 상황",
            "present": "현재 상황",
            "similarity": "유사/상이/부분 유사"
        }
    ],
    "lessons": ["교훈1", "교훈2"],
    "risk_factors": ["리스크1", "리스크2"],
    "opportunities": ["기회1", "기회2"]
}
```
"""
    
    user_prompt = f"""과거 사례: {past_event}
현재 상황: {current_situation}

위 두 상황을 비교 분석해주세요."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0]
        else:
            json_str = content
        
        try:
            result = json.loads(json_str.strip())
            return json.dumps(result, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return json.dumps({
                "analysis": content,
                "comparison_points": [],
                "lessons": [],
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
