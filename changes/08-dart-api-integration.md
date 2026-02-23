# Phase 8: 데이터 소스 연동 (OpenDART API)

## 문제

에이전트가 외부 데이터 소스 없이는 실시간 기업 정보를 제공할 수 없었습니다.

## 해결

### 1. DART 클라이언트 (`dart_client.py`)
금융감독원 전자공시 API 연동:

```python
class DartClient:
    async def get_recent_disclosures(stock_code, days=30) -> dict
    async def get_financial_statements(stock_code, year) -> dict
    async def get_major_shareholders(stock_code) -> dict
```

### 2. 채팅용 포맷팅
```python
async def format_dart_for_chat(stock_code: str, stock_name: str) -> str:
    """
    ### 📋 삼성전자 DART 공시 정보
    
    **최근 공시**
    - [20260220] 분기보고서
    - [20260215] 주요사항보고서
    
    **2025년 재무 하이라이트**
    - 매출액: 302조원
    - 영업이익: 36조원
    """
```

### 3. 슬래시 명령어 연동
`/dart 005930` → 삼성전자 공시 정보 조회

### 4. 자동 시각화
재무 데이터 조회 시 자동으로 트렌드 차트 생성 (기본 옵션)

## 환경 변수

```env
OPEN_DART_API_KEY=your_api_key_here
```

## 변경 파일

- `fastapi/app/services/dart_client.py` (신규)
- `chatbot/skills/data/dart_api.md` (스킬 정의)
