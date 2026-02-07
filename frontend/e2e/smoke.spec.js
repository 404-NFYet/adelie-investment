// @ts-check
import { test, expect } from '@playwright/test';

test.describe('스모크 테스트 - 전체 페이지 렌더링', () => {
  test('홈 페이지가 렌더링된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=키워드')).toBeVisible({ timeout: 10000 });
    // ErrorBoundary 에러 화면이 아닌지 확인
    await expect(page.locator('text=앗, 문제가 생겼어요')).not.toBeVisible();
  });

  test('검색 페이지가 렌더링된다', async ({ page }) => {
    await page.goto('/search');
    await expect(page.locator('input[placeholder*="검색"]')).toBeVisible({ timeout: 5000 });
  });

  test('내러티브 페이지가 렌더링된다', async ({ page }) => {
    await page.goto('/narrative?keyword=test&caseId=6&syncRate=80');
    // STEP 또는 로딩 텍스트가 표시되어야 함
    await expect(page.locator('text=/STEP|로딩/')).toBeVisible({ timeout: 10000 });
  });

  test('API health 엔드포인트가 정상 응답한다', async ({ request }) => {
    const response = await request.get('/api/v1/health');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });
});
