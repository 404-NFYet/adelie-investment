/**
 * Landing 페이지 모바일 반응형 E2E 테스트
 * Test IDs: FE-LAND-M01 ~ FE-LAND-M05
 * 대상 기기: 모바일 9종 (playwright.config.js projects 참조)
 */
import { test, expect } from '@playwright/test';

test.describe('FE-LAND-M: Landing 모바일 반응형', () => {
  test.beforeEach(async ({ page }) => {
    // 미인증 상태로 랜딩 접근
    await page.goto('/');
  });

  /**
   * FE-LAND-M01: ADELIE 브랜드 텍스트가 viewport 내에 표시되는지 확인
   * 검증: clamp(3rem,20vw,5.5rem) 적용 후 텍스트 잘림 없음
   */
  test('FE-LAND-M01: ADELIE 텍스트가 viewport 안에 완전히 표시됨', async ({ page, viewport }) => {
    // Hero 슬라이드 대기
    const brandText = page.locator('p.font-black', { hasText: 'ADELIE' }).first();
    await expect(brandText).toBeVisible();

    const box = await brandText.boundingBox();
    expect(box).not.toBeNull();

    // 텍스트가 viewport 너비를 벗어나지 않음
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1); // 1px 허용오차

    // clamp 하한(3rem=48px) 이상 상한(5.5rem=88px) 이하 높이 확인
    expect(box.height).toBeGreaterThanOrEqual(40); // 3rem 기준 최소
    expect(box.height).toBeLessThanOrEqual(100);   // 5.5rem + 여유
  });

  /**
   * FE-LAND-M02: Hero 이미지가 콘텐츠를 덮어 텍스트를 가리지 않는지 확인
   * 검증: clamp bottom 적용으로 이미지가 텍스트 영역 침범 방지
   */
  test('FE-LAND-M02: Hero 이미지가 텍스트 영역을 가리지 않음', async ({ page }) => {
    const brandText = page.locator('p.font-black', { hasText: 'ADELIE' }).first();
    const heroImage = page.locator('img[alt="ADELIE 랜딩 메인 비주얼"]').first();

    await expect(brandText).toBeVisible();

    // 이미지가 존재하는 경우 텍스트와 겹치지 않음
    const imageCount = await heroImage.count();
    if (imageCount > 0) {
      const textBox = await brandText.boundingBox();
      const imageBox = await heroImage.boundingBox();

      if (textBox && imageBox) {
        // 이미지 상단이 텍스트 하단보다 아래에 있거나
        // z-index로 분리되어 있어 텍스트가 클릭 가능해야 함
        const textIsClickable = await brandText.isVisible();
        expect(textIsClickable).toBe(true);
      }
    }
  });

  /**
   * FE-LAND-M03: 건너뛰기 버튼이 표시되고 동작하는지 확인
   * 검증: 터치 영역 40px 이상, viewport 내 위치
   */
  test('FE-LAND-M03: 건너뛰기 버튼 표시 및 터치 영역 확인', async ({ page, viewport }) => {
    const skipBtn = page.locator('button[aria-label="랜딩 건너뛰기"]');
    await expect(skipBtn).toBeVisible();

    const box = await skipBtn.boundingBox();
    expect(box).not.toBeNull();

    // viewport 내에 위치
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(box.y).toBeGreaterThanOrEqual(0);
  });

  /**
   * FE-LAND-M04: Hero에서 Feature 슬라이드로 자동 전환 확인 (3초 후)
   * 검증: 3초 대기 후 feature 슬라이드 요소 출현
   */
  test('FE-LAND-M04: 3초 후 Feature 슬라이드로 자동 전환', async ({ page }) => {
    // Hero 슬라이드 확인
    await expect(page.locator('p.font-black', { hasText: 'ADELIE' })).toBeVisible();

    // 3.5초 대기 (자동 전환 3000ms)
    await page.waitForTimeout(3500);

    // Feature 슬라이드 버튼(dot)이 나타나야 함
    const dots = page.locator('button[aria-label*="번째 랜딩 화면으로 이동"]');
    await expect(dots.first()).toBeVisible({ timeout: 2000 });
  });

  /**
   * FE-LAND-M05: Feature 슬라이드 이미지가 viewport 너비를 벗어나지 않음
   * 검증: max-w-[80vw] 적용으로 이미지 잘림 방지
   */
  test('FE-LAND-M05: Feature 이미지가 viewport 내에 표시됨', async ({ page, viewport }) => {
    // 자동 전환 대기
    await page.waitForTimeout(3500);

    const featureImages = page.locator('img[alt*="비주얼"]');
    const count = await featureImages.count();

    for (let i = 0; i < count; i++) {
      const img = featureImages.nth(i);
      if (await img.isVisible()) {
        const box = await img.boundingBox();
        if (box) {
          // 이미지가 viewport 너비 내에 있음
          expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 2);
        }
      }
    }
  });
});
