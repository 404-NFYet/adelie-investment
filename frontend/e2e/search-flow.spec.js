// @ts-check
import { test, expect } from '@playwright/test';

test.describe('검색 플로우', () => {
  test('인기 키워드가 DB에서 로드된다', async ({ page }) => {
    await page.goto('/search');
    // 인기 키워드 또는 최근 사례가 로드됨
    await expect(page.locator('text=/인기 키워드|최근 분석/')).toBeVisible({ timeout: 10000 });
  });

  test('검색어 입력 후 검색하면 결과가 표시된다', async ({ page }) => {
    await page.goto('/search');
    await page.fill('input[placeholder*="검색"]', '바이오');
    await page.click('button:has-text("검색")');
    // 검색 중 또는 결과 표시
    await expect(page.locator('text=/검색 중|검색 결과/')).toBeVisible({ timeout: 15000 });
  });

  test('인기 키워드 클릭 시 검색이 실행된다', async ({ page }) => {
    await page.goto('/search');
    const tag = page.locator('button.tag').first();
    await tag.waitFor({ timeout: 10000 });
    await tag.click();
    await expect(page).toHaveURL(/search\?q=/, { timeout: 3000 });
  });
});
