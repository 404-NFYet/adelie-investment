# Frontend 교차 의존성

프론트엔드가 다른 파트의 변경에 영향을 받는 지점과 대응 방법을 정리한다.

## 1. Backend API (FastAPI)

### 의존 관계
- 프론트엔드의 모든 데이터는 `GET/POST /api/v1/*` 엔드포인트에서 온다
- `src/api/client.js`의 `fetchJson`/`postJson`이 공통 HTTP 클라이언트
- 도메인별 API 함수: `src/api/auth.js`, `narrative.js`, `portfolio.js`

### 영향 받는 변경
| 백엔드 변경 | 프론트 대응 |
|-------------|-----------|
| 응답 스키마 필드 변경 | 해당 API 함수 + 소비 컴포넌트 수정 |
| 엔드포인트 경로 변경 | `src/api/` 해당 파일 수정 |
| 인증 방식 변경 | `client.js`의 Authorization 헤더 로직 수정 |
| 새 API 추가 | `src/api/`에 함수 추가, 필요 시 새 파일 생성 |
| 에러 응답 형식 변경 | `client.js`의 에러 핸들링 로직 수정 |

### 확인 방법
```bash
# 백엔드 스키마 확인
curl http://localhost:8082/docs          # Swagger UI
curl http://localhost:8082/openapi.json  # OpenAPI 스펙
```

## 2. Chatbot (SSE 스트리밍)

### 의존 관계
- 튜터 대화: `POST /api/v1/tutor/chat` → SSE (Server-Sent Events) 스트리밍 응답
- `TutorContext.jsx`에서 SSE 연결 관리
- `components/tutor/` 디렉토리에서 스트리밍 메시지를 실시간 렌더링

### 영향 받는 변경
| 챗봇 변경 | 프론트 대응 |
|-----------|-----------|
| SSE 이벤트 포맷 변경 | `TutorContext.jsx`의 SSE 파싱 로직 수정 |
| 새 도구 출력 (차트, 표 등) | `components/tutor/`에 렌더러 추가 |
| 난이도 옵션 변경 | 난이도 선택 UI 수정 |
| 용어 하이라이트 포맷 변경 | `TermContext.jsx` + `TermBottomSheet` 수정 |

### SSE 이벤트 타입
현재 지원하는 SSE 이벤트:
- `content` — 텍스트 스트리밍 (토큰 단위)
- `chart` — 차트 데이터 (Plotly JSON)
- `done` — 스트리밍 완료
- `error` — 에러 메시지

## 3. Data Pipeline 출력

### 의존 관계
- 파이프라인이 생성한 데이터가 DB에 저장되고, 백엔드 API를 통해 프론트에 전달
- 직접 의존은 없으나, 데이터 구조 변경 시 간접적으로 영향

### 영향 받는 변경
| 파이프라인 변경 | 프론트 대응 |
|----------------|-----------|
| 키워드 카드 구조 변경 | `Home.jsx` 키워드 카드 렌더링 수정 |
| 내러티브 본문 마크다운 포맷 변경 | `Narrative.jsx`의 React Markdown 렌더링 확인 |
| 차트 데이터 스키마 변경 | `components/charts/` 차트 컴포넌트 수정 |
| 새 데이터 필드 추가 | 백엔드 API 스키마에 포함되면 UI에서 표시 여부 결정 |

## 4. 환경변수

### 프론트엔드 환경변수
| 변수 | 용도 | 기본값 |
|------|------|--------|
| `VITE_FASTAPI_URL` | 로컬 개발 시 백엔드 주소 | (빈 문자열 — nginx 프록시) |

> Vite 환경변수는 `VITE_` 접두사가 필요하다. 빌드 타임에 인라인되므로 시크릿을 넣으면 안 된다.

### 프로덕션 vs 개발
| 환경 | API base URL | 설정 위치 |
|------|-------------|----------|
| 프로덕션 (Docker) | 빈 문자열 → nginx `/api/v1/*` 프록시 | `nginx.conf` |
| 로컬 개발 | `http://localhost:8082` 또는 `http://10.10.10.14:8082` | `.env`의 `VITE_FASTAPI_URL` |

## 5. 변경 대응 프로세스

1. **다른 파트에서 PR 올릴 때** — 프론트 영향 여부를 PR 설명에 명시
2. **스키마 변경 시** — 백엔드 담당자가 Swagger 문서 업데이트 후 프론트 담당자에게 공유
3. **SSE 포맷 변경 시** — 챗봇 담당자가 이벤트 타입과 페이로드 구조를 문서화
4. **통합 테스트** — `make test-e2e`로 전체 플로우 확인
