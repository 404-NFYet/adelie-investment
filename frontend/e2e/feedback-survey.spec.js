// @ts-check
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

test.describe('피드백 설문 폼 (FE-SURVEY)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/auth`);
    await page.evaluate(() => {
      localStorage.setItem('token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 1, username: 'tester', isAuthenticated: true }));
    });
  });

  test('FE-SURVEY-01: 프로필 → 설문 페이지 진입', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);
    await page.getByText('서비스 평가하기').click();
    await expect(page).toHaveURL(/feedback-survey/);
    await expect(page.getByText('아델리에 서비스 평가')).toBeVisible();
  });

  test('FE-SURVEY-02: 1~5점 선택 UI 동작', async ({ page }) => {
    await page.goto(`${BASE_URL}/feedback-survey`);
    // 5개 항목 각각 5점 선택
    const cards = page.locator('.card');
    for (let i = 0; i < 5; i++) {
      const card = cards.nth(i);
      const scoreBtn = card.getByText('5', { exact: true });
      await scoreBtn.click();
      // 선택된 버튼 primary 색상 확인
      await expect(scoreBtn).toHaveClass(/bg-primary/);
    }
    // 모든 항목 선택 후 제출 버튼 활성화
    const submitBtn = page.getByText('제출하기');
    await expect(submitBtn).toBeEnabled();
  });

  test('FE-SURVEY-03: 자유 의견 입력', async ({ page }) => {
    await page.goto(`${BASE_URL}/feedback-survey`);
    const textarea = page.locator('#survey-comment');
    await textarea.fill('매우 유익한 서비스입니다');
    // 글자 수 표시 확인
    await expect(page.getByText(/\d+\/2000/)).toBeVisible();
  });

  test('FE-SURVEY-04: 스크린샷 첨부', async ({ page }) => {
    await page.goto(`${BASE_URL}/feedback-survey`);
    // 파일 선택
    const fileInput = page.locator('input[type="file"]');
    // 테스트 이미지 생성 (1x1 PNG)
    const buffer = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');
    await fileInput.setInputFiles({
      name: 'test-screenshot.png',
      mimeType: 'image/png',
      buffer,
    });
    // 미리보기 표시 확인
    await expect(page.locator('img[alt="첨부된 스크린샷"]')).toBeVisible();
  });

  test('FE-SURVEY-05: 미선택 항목 존재 시 제출 불가', async ({ page }) => {
    await page.goto(`${BASE_URL}/feedback-survey`);
    // 일부만 선택
    const cards = page.locator('.card');
    await cards.nth(0).getByText('3', { exact: true }).click();
    await cards.nth(1).getByText('4', { exact: true }).click();
    // 제출 버튼 비활성
    await expect(page.getByText('제출하기')).toBeDisabled();
    // 안내 메시지 확인
    await expect(page.getByText('모든 항목을 평가해주세요')).toBeVisible();
  });
});
