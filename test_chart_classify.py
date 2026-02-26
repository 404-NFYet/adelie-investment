import asyncio
import os
from chatbot.services.tutor_chart_generator import classify_chart_request

async def test():
    req = "셀트리온의 최근 일주일간 주가 차트를 보여줘"
    ctx = """셀트리온의 최근 일주일간 주가를 차트로 보여드릴게요! 아래는 셀트리온 주가의 일주일간 변동을 시각화한 그래프입니다.

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
(주가는 대략적으로 표시된 것입니다)

19일: 244,500원
20일: 242,000원
23일: 243,000원
24일: 248,500원
25일: 244,500원
차트에서 볼 수 있듯이 주가는 22일을 제외하고 전체적으로 오르내림이 있었고, 특히 24일에 가장 높은 가격을 기록한 후 다시 하락하는 모습을 보여주고 있습니다.

이런 변동은 대장주인 알테오젠의 부진에 따른 영향으로 보이며, 바이오 섹터 전반에 심리적 영향을 주고 있습니다.

혹시 더 알아보고 싶은 내용이 있을까요?"""

    res = await classify_chart_request(req, ctx)
    print(res.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(test())
