# 테스트 가이드

## 테스트 실행 명령어

```bash
# 전체 테스트
make test

# 백엔드 테스트 (pytest)
make test-backend

# E2E 테스트 (Playwright)
make test-e2e

# 부하 테스트 (Locust, 40명)
make test-load

# 파이프라인 검증
make test-pipeline

# AI QA 테스트 (환각 검증)
cd fastapi && pytest ai-qa-tests/ -v
```

## 테스트 구조

```
tests/
  conftest.py                    # pytest 공통 설정
  unit/
    test_prompt_loader.py        # 프롬프트 로더
    test_services.py             # 서비스 레이어
    test_schemas.py              # Pydantic 스키마
    test_collectors.py           # 데이터 수집기
    test_ai_tools.py             # AI 도구
  backend/
    test_api_health.py           # 헬스체크 API
    test_api_smoke.py            # 스모크 테스트
    test_api_cases.py            # 케이스 API
    test_api_glossary.py         # 용어 사전 API
    test_api_pipeline.py         # 파이프라인 API
    test_api_tutor.py            # AI 튜터 API (SSE)
  integration/
    phase0_tests.py              # 외부 서비스 통합 테스트
    test_viz_model_comparison.py # 시각화 모델 비교
  load/
    locustfile.py                # 40인 부하 테스트

datapipeline/tests/
    test_data_collection.py      # 데이터 수집 테스트
    test_data_collection_utils.py# 수집 유틸 테스트
    test_nodes.py                # 파이프라인 노드 테스트
    test_schemas.py              # 스키마 테스트

frontend/e2e/
  smoke.spec.js                  # 스모크 테스트
  auth-flow.spec.js              # 인증 플로우
  narrative-flow.spec.js         # 내러티브 플로우
  tutor-chat.spec.js             # 튜터 채팅
  search-flow.spec.js            # 검색
  home-keywords.spec.js          # 키워드
  onboarding.spec.js             # 온보딩
  mobile-full-flow.spec.js       # 모바일 전체 플로우
  ...

fastapi/ai-qa-tests/
  test_hallucination.py          # AI 환각 검증
```

## 새 테스트 작성법

### Backend (pytest)

```python
# tests/test_api_xxx.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_my_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

### Frontend E2E (Playwright)

```javascript
// frontend/e2e/my-flow.spec.js
import { test, expect } from '@playwright/test';

test.describe('My Feature', () => {
  test('should work correctly', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=아델리에')).toBeVisible();
  });
});
```

### 부하 테스트 (Locust)

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def my_task(self):
        self.client.get("/api/v1/my-endpoint")
```

실행: `locust -f tests/load/locustfile.py --headless -u 40 -r 5 --run-time 2m`

## Docker 기반 테스트

```bash
# 격리된 테스트 환경에서 실행
docker compose -f docker-compose.test.yml up --abort-on-container-exit

# E2E 테스트 (Playwright + 앱 서비스)
docker compose -f docker-compose.test.yml --profile e2e up --abort-on-container-exit
```
