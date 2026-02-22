// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
};

test.describe('케이스 리다이렉트 (FE-CASE)', () => {
  test('FE-CASE-01: /case/:id 접근 시 /narrative/:id 또는 홈으로 리다이렉트된다', async ({ page }) => {
    await page.goto('/case/6');
    await page.waitForTimeout(2000);
    const url = page.url();
    // /narrative/6 또는 /narrative?caseId=6 으로 이동하거나 홈으로 리다이렉트
    const isRedirected =
      url.includes('/narrative') ||
      url.includes('/story') ||
      url.endsWith('/') ||
      url.includes('/home');
    expect(isRedirected).toBe(true);
  });

  test('FE-CASE-02: 존재하지 않는 /case/99999 접근 시 오류 메시지 또는 홈 리다이렉트', async ({ page }) => {
    await page.goto('/case/99999');
    await page.waitForTimeout(2000);
    const url = page.url();
    // 1) 홈 또는 다른 페이지로 리다이렉트
    const isRedirected = !url.includes('/case/99999') || url.endsWith('/');
    // 2) 에러 메시지 표시
    const hasError = await page
      .getByText(/찾을 수 없|없는 케이스|404|오류|에러|존재하지/)
      .isVisible({ timeout: TIMEOUT.fast })
      .catch(() => false);
    expect(isRedirected || hasError).toBe(true);
  });
});
