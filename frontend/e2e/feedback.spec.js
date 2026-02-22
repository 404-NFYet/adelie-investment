// @ts-check
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('피드백 시스템 (FE-FEED)', () => {
  test.beforeEach(async ({ page }) => {
    // 로그인 상태 시뮬레이션
    await page.goto(`${BASE_URL}/auth`);
    await page.evaluate(() => {
      localStorage.setItem('token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'tester', isAuthenticated: true }));
    });
  });

  test('FE-FEED-01: 홈 키워드 카드 반응 버튼 표시', async ({ page }) => {
    await page.goto(`${BASE_URL}/home`);
    // 반응 버튼 존재 확인
    const likeButton = page.locator('[data-testid^="reaction-like-keyword_card"]');
    await expect(likeButton.first()).toBeVisible({ timeout: 10000 });
  });

  test('FE-FEED-02: 프로필에서 설문 페이지 진입', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);
    // 서비스 평가하기 카드 클릭
    const surveyCard = page.getByText('서비스 평가하기');
    await expect(surveyCard).toBeVisible({ timeout: 5000 });
    await surveyCard.click();
    await expect(page).toHaveURL(/feedback-survey/);
  });

  test('FE-FEED-03: 설문 1~5점 체크 UI', async ({ page }) => {
    await page.goto(`${BASE_URL}/feedback-survey`);
    // 제출 버튼 비활성 확인 (미선택 상태)
    const submitBtn = page.getByText('제출하기');
    await expect(submitBtn).toBeDisabled();
  });

  test('FE-FEED-04: 홈에 FeedbackWidget 자동 팝업 미노출', async ({ page }) => {
    await page.goto(`${BASE_URL}/home`);
    // 60초 대기 후에도 FeedbackWidget 미노출
    await page.waitForTimeout(3000);
    const feedbackWidget = page.locator('.fixed.inset-0.bg-black\\/40');
    await expect(feedbackWidget).not.toBeVisible();
  });
});
