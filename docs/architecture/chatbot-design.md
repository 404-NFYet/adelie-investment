# 아델리 AI 튜터 설계 문서

## 목적

한국 주식시장 초보 투자자에게 금융 교육을 제공하는 AI 튜터.
"역사는 반복된다" 컨셉에 맞춰, 현재 시장 이슈와 과거 사례를 연결하여 설명.

## 데이터 소스 & 컨텍스트 계층

| 레이어 | 소스 | 주입 시점 | 용도 |
|--------|------|-----------|------|
| L1. 시스템 프롬프트 | `tutor_system.md` + 난이도별 `.md` | 세션 시작 | 페르소나, 톤, 교육 수준 |
| L2. 용어 사전 | `glossary` DB 테이블 | 매 메시지 | 용어 정의, 하이라이트 |
| L3. 오늘의 브리핑 | `daily_briefings` + `daily_narratives` | 매 메시지 | 오늘 시장 뉴스, 키워드 |
| L4. 과거 사례 | `historical_cases` + `case_matches` | 매 메시지 | 유사 역사 사례 비교 |
| L5. 포트폴리오 | `portfolios` + `limit_orders` (JWT) | 인증 시 | 사용자 보유 종목 맞춤 응답 |
| L6. 종목 데이터 | `stock_listings` + 실시간 시세 | 요청 시 | 종목 정보, 차트 생성 |

## 페이지별 맥락 인식

| 페이지 | 진입 컨텍스트 | 프리뷰 프롬프트 |
|--------|-------------|----------------|
| Home (키워드 목록) | 오늘의 키워드 n개 | "오늘 시장 뉴스 요약해주세요" |
| Narrative (상세) | 현재 키워드 + 과거 사례 | "이 사례를 쉽게 설명해주세요" |
| Portfolio | 보유 종목 리스트 | "내 포트폴리오 오늘 뉴스 영향은?" |
| Search | 검색 키워드 | "검색한 종목에 대해 알려주세요" |
| 기본 | 없음 | "주식 시장 기초부터 알려주세요" |

## 난이도 시스템

| 난이도 | 대상 | 특징 |
|--------|------|------|
| beginner | 주식 처음 | 비유 중심, 공식 없음, 일상 용어 |
| elementary | 기본 이해 | 기본 재무 용어 (PER, PBR), 간단한 수학 |
| intermediate | 중급자 | ROE/ROIC/FCF, DCF, 섹터 순환 |

## 프롬프트 파일 구조

```
chatbot/prompts/templates/
├── tutor_system.md         # 시스템 프롬프트 (페르소나, 기본 규칙)
├── tutor_beginner.md       # beginner 난이도 지시사항
├── tutor_elementary.md     # elementary 난이도 지시사항
├── tutor_intermediate.md   # intermediate 난이도 지시사항
├── _tone_guide.md          # 톤 가이드 (~해요체, 조언 금지, 스토리텔링)
└── term_explanation.md     # 용어 설명 응답 포맷
```

## 기술 구현

- **SSE 스트리밍**: `POST /api/v1/tutor/chat` → Server-Sent Events
- **세션 관리**: `TutorSession` + `TutorMessage` DB 모델, localStorage에 session_id 유지
- **세션 히스토리**: `GET /api/v1/tutor/sessions/{session_id}/messages`
- **시각화**: Claude 3.5 Haiku로 Plotly JSON 생성, OpenAI GPT-4o fallback
- **용어 하이라이트**: `term_highlighter.py`로 응답 내 금융 용어 자동 감지

## 데이터 의존성

```
ChatFAB 활성화
  ├── tutor_engine.py 서비스 정상
  │     ├── OpenAI API 키 (.env)
  │     ├── gpt-4o-mini 모델 접근 가능
  │     └── Claude 3.5 Haiku (시각화 fallback)
  ├── DB 데이터 존재
  │     ├── daily_briefings (오늘의 브리핑)
  │     ├── daily_narratives (상세 내러티브)
  │     ├── historical_cases (과거 사례)
  │     ├── case_matches (현재-과거 매칭)
  │     ├── glossary (용어 사전)
  │     └── stock_listings (종목 목록)
  ├── 세션 관리
  │     ├── TutorSession 모델 (DB)
  │     ├── TutorMessage 모델 (DB)
  │     └── 세션 히스토리 API
  └── 프론트엔드
        ├── TutorContext.jsx (상태 관리)
        ├── TutorModal.jsx (UI)
        └── ChatFAB.jsx (진입점)
```
