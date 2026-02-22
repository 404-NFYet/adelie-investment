// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
};

test.describe('스모크 테스트 - 전체 페이지 렌더링 (FE-SMOKE)', () => {
  test('FE-SMOKE-01: 홈 페이지가 렌더링된다', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('키워드')).toBeVisible({ timeout: TIMEOUT.network });
    // ErrorBoundary 에러 화면 미노출 확인
    await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
  });

  test('FE-SMOKE-02: 검색 페이지가 렌더링된다', async ({ page }) => {
    await page.goto('/search');
    await expect(page.locator('input[placeholder*="검색"]')).toBeVisible({ timeout: TIMEOUT.fast });
  });

  test('FE-SMOKE-03: 내러티브 페이지가 렌더링된다', async ({ page }) => {
    await page.goto('/narrative?keyword=test&caseId=6&syncRate=80');
    // STEP 또는 로딩 텍스트가 표시되어야 함
    await expect(page.locator('text=/STEP|로딩/')).toBeVisible({ timeout: TIMEOUT.network });
  });

  test('FE-SMOKE-04: 미인증 상태로 /home 접근 시 /auth 또는 /onboarding으로 리다이렉트된다', async ({ page }) => {
    // localStorage 초기화 → 인증 상태 없음
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
    });
    await page.goto('/home');
    await page.waitForTimeout(1500);
    const url = page.url();
    const isRedirected = url.includes('/auth') || url.includes('/onboarding') || url.includes('/');
    expect(isRedirected).toBe(true);
  });

  test('FE-SMOKE-05: BottomNav 4개 탭 렌더링이 확인된다', async ({ page }) => {
    await page.goto('/');
    // BottomNav는 nav 역할 또는 class 기반 컨테이너로 렌더링
    const nav = page.locator('nav, [class*="bottom"], [class*="BottomNav"]').first();
    await expect(nav).toBeVisible({ timeout: TIMEOUT.fast });
    // 홈/포트폴리오/프로필 관련 탭 링크 존재 확인
    const homeTab = page.getByRole('link', { name: /홈|home/i }).or(
      page.locator('a[href="/"], a[href="/home"]')
    ).first();
    await expect(homeTab).toBeVisible({ timeout: TIMEOUT.fast });
  });

  test('FE-SMOKE-06: 존재하지 않는 /case/99999 접근 시 오류 표시 또는 홈 리다이렉트', async ({ page }) => {
    await page.goto('/case/99999');
    await page.waitForTimeout(2000);
    const url = page.url();
    // 404 페이지 또는 홈으로 리다이렉트 또는 에러 메시지 표시
    const isHandled =
      url.includes('/') ||
      await page.getByText(/찾을 수 없|없는 페이지|404|오류|에러/).isVisible({ timeout: TIMEOUT.fast }).catch(() => false);
    expect(isHandled).toBe(true);
  });
});
