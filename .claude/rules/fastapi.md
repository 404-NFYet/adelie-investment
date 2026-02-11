---
paths:
  - "fastapi/**/*.py"
---

# FastAPI 코드 컨벤션

## 모델 (SQLAlchemy)
- `app.core.database.Base` 상속, `mapped_column` 사용
- 테이블명은 snake_case 복수형 (e.g., `historical_cases`)
- 관계 정의 시 `relationship()` with `back_populates`

## 스키마 (Pydantic v2)
- `app/schemas/` 디렉토리에 도메인별 파일
- `model_config = ConfigDict(from_attributes=True)` 사용
- 응답 스키마는 `{Model}Response`, 요청은 `{Model}Request`

## 라우트
- `APIRouter(prefix="/{도메인}")` 패턴
- `main.py`에서 `/api/v1` 프리픽스로 자동 마운트
- 비동기 핸들러: `async def` 사용
- 의존성 주입: `Depends(get_db)` for DB 세션

## API 응답 형식
- 성공: `{"status": "success", "data": ...}`
- 에러: `HTTPException`으로 적절한 status code 반환
- 리스트: `{"status": "success", "data": [...], "total": N}`

## 기타
- 한글 주석 사용
- `.env`에서 환경변수 로드 (`app.core.config.settings`)
- async/await 일관성 유지 (sync 함수 혼용 금지)
