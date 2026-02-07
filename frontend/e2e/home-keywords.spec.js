// @ts-check
import { test, expect } from '@playwright/test';

test.describe('홈 - 키워드 플로우', () => {
  test('키워드가 1개 이상 로드되거나 준비 중 메시지가 표시된다', async ({ page }) => {
    await page.goto('/');
    // 키워드 카드 또는 "준비 중" 메시지
    const hasKeywords = page.locator('[class*="card"]').first();
    const preparing = page.locator('text=준비 중');
    await expect(hasKeywords.or(preparing)).toBeVisible({ timeout: 10000 });
  });

  test('키워드 선택 후 START BRIEFING 버튼이 나타난다', async ({ page }) => {
    await page.goto('/');
    // 첫 번째 카드 클릭
    const firstCard = page.locator('[class*="card"]').first();
    await firstCard.waitFor({ timeout: 10000 });
    await firstCard.click();
    // START BRIEFING 버튼 확인
    await expect(page.locator('text=START BRIEFING')).toBeVisible({ timeout: 3000 });
  });
});
