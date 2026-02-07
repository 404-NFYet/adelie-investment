// @ts-check
import { test, expect } from '@playwright/test';

test.describe('AI 튜터 시각화', () => {
  test('급등주 차트 요청 시 차트 또는 에러가 표시된다', async ({ page }) => {
    await page.goto('/');
    // AI 튜터 열기
    const fab = page.locator('text=AI 튜터').first();
    await fab.waitFor({ timeout: 5000 });
    await fab.click();
    await expect(page.locator('text=질문을 입력하세요')).toBeVisible({ timeout: 3000 });

    // 급등주 차트 버튼 클릭
    const chartBtn = page.locator('button:has-text("급등주")');
    if (await chartBtn.isVisible({ timeout: 2000 })) {
      await chartBtn.click();
      // 차트(iframe) 또는 에러 메시지 대기
      const chart = page.locator('iframe[title="차트"]');
      const error = page.locator('text=/차트 생성 실패|에러/');
      await expect(chart.or(error)).toBeVisible({ timeout: 30000 });
    }
  });
});
