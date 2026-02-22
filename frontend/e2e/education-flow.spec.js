// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
};

test.describe('교육 플로우 (FE-EDU)', () => {
  test('FE-EDU-01: 교육 페이지(/education)가 로드된다', async ({ page }) => {
    await page.goto('/education');
    await page.waitForLoadState('networkidle');
    // 교육/학습 관련 텍스트 또는 탭 존재 확인
    const eduEl = page.getByText(/교육|학습|활동|achievement/i).first();
    await expect(eduEl).toBeVisible({ timeout: TIMEOUT.network });
    await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
  });

  test('FE-EDU-02: 활동 아카이브(/education/archive) 페이지가 로드된다', async ({ page }) => {
    await page.goto('/education/archive');
    await page.waitForLoadState('networkidle');
    // 아카이브 관련 텍스트 또는 날짜 캘린더 UI 확인
    const archiveEl = page.getByText(/아카이브|활동 기록|기록|archive/i).first();
    const calendarEl = page.locator('[class*="calendar"], [class*="Calendar"]').first();
    await expect(archiveEl.or(calendarEl)).toBeVisible({ timeout: TIMEOUT.network });
    await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
  });

  test('FE-EDU-03: 아카이브 페이지에서 날짜별 목록 또는 캘린더 UI가 표시된다', async ({ page }) => {
    await page.goto('/education/archive');
    await page.waitForLoadState('networkidle');
    // 날짜 기반 UI (캘린더, 날짜 표시, 리스트) 중 하나 확인
    const dateEl = page.locator('time, [class*="date"], [class*="month"], [class*="year"]').first();
    const listEl = page.locator('[class*="list"], [class*="item"], li').first();
    await expect(dateEl.or(listEl)).toBeVisible({ timeout: TIMEOUT.network });
  });
});

// ─── 모바일 테스트 (390px) ────────────────────────────────────

test.describe('교육 모바일 (FE-EDU-M)', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('FE-EDU-M01: 모바일(390px) 교육 페이지 레이아웃이 깨지지 않는다', async ({ page }) => {
    await page.goto('/education');
    await page.waitForLoadState('networkidle');
    await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
    // 뷰포트 오버플로우 미발생 확인
    const bodyBox = await page.locator('body').boundingBox();
    expect(bodyBox.width).toBeLessThanOrEqual(390 + 5);
  });
});
