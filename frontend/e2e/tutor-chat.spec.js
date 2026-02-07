// @ts-check
import { test, expect } from '@playwright/test';

test.describe('AI 튜터 채팅', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // AI 튜터 FAB 클릭
    const fab = page.locator('text=AI 튜터').first();
    await fab.waitFor({ timeout: 5000 });
    await fab.click();
    // 모달이 열릴 때까지 대기
    await expect(page.locator('text=질문을 입력하세요')).toBeVisible({ timeout: 3000 });
  });

  test('메시지를 전송하면 AI 응답이 표시된다', async ({ page }) => {
    await page.fill('input[placeholder*="질문"]', 'PER이 뭔가요?');
    await page.click('button:has-text("전송")');
    // AI 응답 대기 (최대 15초)
    await expect(page.locator('text=AI 튜터').nth(1)).toBeVisible({ timeout: 15000 });
  });

  test('빠른 질문 버튼을 클릭하면 바로 응답이 시작된다', async ({ page }) => {
    const quickBtn = page.locator('button:has-text("PER이 뭔가요")');
    if (await quickBtn.isVisible()) {
      await quickBtn.click();
      // 로딩 또는 응답 확인
      await expect(page.locator('text=/분석 중|AI 튜터/')).toBeVisible({ timeout: 10000 });
    }
  });
});
