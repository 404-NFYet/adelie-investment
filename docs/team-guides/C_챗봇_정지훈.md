# 챗봇 개발 가이드 — 정지훈

## 환경 정보
- LXD 컨테이너: `ssh dev-j2hoon10`
- Git 설정: user.name=J2hoon10, user.email=myhome559755@naver.com
- 브랜치: `dev/chatbot`

## 개발 시작

### Docker 환경 (권장)
```bash
make dev-api
# backend-api 컨테이너가 chatbot 모듈을 포함
```
- Tutor API: http://localhost:8082/api/v1/tutor/chat (SSE)
- FastAPI auto-reload 활성화 → `chatbot/` 수정 시 자동 재시작

### 로컬 환경 (Docker 없이)
```bash
cd fastapi
source ../.venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```
- `.env`에서 `OPENAI_API_KEY`, `LANGCHAIN_API_KEY` 확인
- chatbot 모듈이 `sys.path`에 자동 포함됨 (fastapi/app/main.py에서 처리)

## 담당 디렉토리

```
chatbot/
├── agent/
│   ├── tutor_agent.py           # LangGraph 상태 머신 정의
│   ├── prompts.py               # 시스템 프롬프트, 난이도별 프롬프트
│   └── checkpointer.py          # PostgresSaver (대화 기록 저장)
├── tools/                       # LangChain 도구 (튜터가 호출 가능)
│   ├── search_tool.py           # 브리핑/뉴스 검색
│   ├── briefing_tool.py         # 오늘의 키워드 조회
│   ├── comparison_tool.py       # 과거-현재 비교
│   ├── visualization_tool.py    # 차트 생성 요청
│   ├── glossary_tool.py         # 용어 설명
│   └── portfolio_tool.py        # 포트폴리오 조회
├── services/
│   ├── term_highlighter.py      # 용어 하이라이트 서비스
│   └── ...
├── prompts/                     # 마크다운 프롬프트 템플릿
│   ├── tutor_system.md
│   ├── tutor_beginner.md
│   ├── tutor_intermediate.md
│   └── tutor_advanced.md
└── core/
    ├── config.py                # Chatbot 환경변수 설정
    └── langsmith.py             # LangSmith 추적 설정

fastapi/app/
├── api/routes/tutor.py          # Tutor API 라우터 (/api/v1/tutor/*)
└── services/tutor_engine.py     # chatbot 모듈 import, SSE 스트리밍
```

### 핵심 파일
- `agent/tutor_agent.py`: LangGraph StateGraph, 노드(call_model, run_tools), 엣지 정의
- `tools/*.py`: `@tool` 데코레이터로 정의된 LangChain 도구
- `services/term_highlighter.py`: 튜터 응답에서 용어 자동 하이라이트
- `fastapi/app/api/routes/tutor.py`: SSE 엔드포인트, 세션 관리, 대화 기록 조회

## 개발 워크플로우

1. **새 도구 추가**
   ```python
   # chatbot/tools/new_tool.py
   from langchain.tools import tool

   @tool
   def new_tool(query: str) -> str:
       """도구 설명 (LLM이 읽음)"""
       # 비즈니스 로직
       return result

   # agent/tutor_agent.py에 도구 등록
   tools = [search_tool, briefing_tool, new_tool]
   ```

2. **프롬프트 수정**
   - `prompts/tutor_system.md` 또는 난이도별 프롬프트 편집
   - `agent/prompts.py`에서 load_prompt() 호출
   - FastAPI 재시작 시 자동 로드

3. **SSE 이벤트 추가**
   ```python
   # fastapi/app/api/routes/tutor.py
   async for event in graph.astream_events(...):
       if event["event"] == "on_custom_event":
           yield f"event: custom\ndata: {json.dumps(data)}\n\n"
   ```
   - Frontend `TutorContext.jsx`에서 `eventSource.addEventListener('custom', ...)` 추가

4. **대화 기록 관리**
   - `checkpointer.py`의 PostgresSaver가 자동 저장
   - thread_id = `{user_id}_{session_id}` 형식
   - 히스토리 조회: `GET /api/v1/tutor/history?thread_id=...`

## 테스트

### Unit 테스트
```bash
# chatbot 도구 테스트
pytest tests/unit/test_chatbot_tools.py -v

# 로컬 실행
source .venv/bin/activate
pytest tests/unit/test_chatbot_tools.py::test_search_tool -v
```

### 수동 테스트 (SSE)
```bash
# curl로 SSE 스트림 확인
curl -N -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8082/api/v1/tutor/chat?message=삼성전자%20분석해줘"
```

### LangSmith 추적
- 대시보드: https://smith.langchain.com
- `.env`에서 `LANGCHAIN_API_KEY`, `LANGCHAIN_TRACING_V2=true` 확인
- 모든 LLM 호출, 도구 실행 자동 로깅

## 다른 파트와의 연동

### Backend (허진서)
- **영향받는 경우**: DB 모델 변경 (users, portfolios, keywords, cases, glossary)
- **대응**: 도구에서 DB 쿼리 수정 (예: `portfolio_tool.py`, `glossary_tool.py`)
- **주의**:
  - JWT 인증 로직 변경 → `tutor.py`의 `get_current_user_optional` 확인
  - DB 세션은 FastAPI dependency로 주입받음

### Frontend (손영진)
- **영향주는 경우**: SSE 이벤트 타입 추가/변경, 응답 포맷 변경
- **알림 필요**:
  - 새 이벤트 타입 → `TutorContext.jsx`에 addEventListener 추가
  - 용어 하이라이트 포맷 변경 → `ChatMessage.jsx` 렌더링 로직 수정
- **주의**:
  - `event: message` → 일반 텍스트
  - `event: term_highlight` → 용어 하이라이트 데이터
  - `event: tool_call` → 도구 실행 중 알림

### Pipeline (안례진)
- **영향받는 경우**: glossary 구조 변경, narrative 포맷 변경
- **대응**:
  - `glossary_tool.py` → DB 쿼리 수정
  - `briefing_tool.py`, `comparison_tool.py` → 응답 파싱 로직 수정
- **주의**: Pipeline이 생성한 데이터를 튜터가 검색/표시 → 스키마 일관성 중요

### Infra (도형준)
- **영향받는 경우**: Docker 이미지 재빌드, LangSmith API 키 변경
- **협업 필요**:
  - `.env.example`에 `LANGCHAIN_API_KEY`, `OPENAI_API_KEY` 추가
  - `docker-compose.*.yml`에 환경변수 전달 확인
- **주의**: chatbot은 backend-api 이미지에 포함 → fastapi Dockerfile 확인

## 커밋 전 체크리스트
- [ ] `git config user.name` = J2hoon10
- [ ] `git config user.email` = myhome559755@naver.com
- [ ] 새 도구는 단위 테스트 작성
- [ ] SSE 이벤트 변경 시 Frontend 팀에 알림
- [ ] LangSmith에서 추적 로그 확인 (오류 없는지)
- [ ] 프롬프트 변경 시 응답 품질 수동 검증
- [ ] 커밋 메시지 형식: `feat: 튜터에 포트폴리오 분석 도구 추가` (한글, type prefix)
