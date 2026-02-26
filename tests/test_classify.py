import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, '/app')

from chatbot.services.tutor_chart_generator import classify_chart_request

async def test_classify():
    user_req = "셀트리온의 최근 일주일간 주가 차트를 보여줘"
    full_resp = """셀트리온의 최근 일주일간 주가를 차트로 보여드릴게요! 아래는 셀트리온 주가의 일주일간 변동을 시각화한 그래프입니다.

셀트리온 최근 일주일간 주가 차트
주가(원)
|
|            *
|          *    
|         *     
|         |      *  
|         |     *     
|         |   *       
|         | *          
|         |____________
|            19  20  23  24  25
|_______________ 날짜
"""
    res = await classify_chart_request(user_req, full_resp)
    print("Classification Result:")
    print(f"Reasoning: {res.reasoning}")
    print(f"Chart Type: {res.chart_type}")

if __name__ == "__main__":
    asyncio.run(test_classify())
