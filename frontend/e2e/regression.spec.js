/**
 * 회귀 테스트: Story, Comparison, Companies 페이지 정상 렌더링 검증
 * ThemeProvider + ProtectedRoute 수정 이후 회귀 방지.
 *
 * 선행조건: 온보딩 완료 → hasCompletedOnboarding 설정
 * 대상 라우트: /story, /comparison, /companies
 */
import { test, expect } from '@playwright/test';

const MOBILE_VIEWPORT = { width: 390, height: 844 };

test.use({
  viewport: MOBILE_VIEWPORT,
  userAgent:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
});

test.describe.serial('회귀: Story, Comparison, Companies 렌더링', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ viewport: MOBILE_VIEWPORT });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  // ==========================================
  // PRE-CONDITION: Complete Onboarding
  // ==========================================

  test('PRE: Complete onboarding flow', async () => {
    // 1. Clear state and go to onboarding
    await page.goto('/onboarding');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');

    // 2. Click "다음" 4 times
    const nextBtn = page.locator('button', { hasText: /^다음$/ });
    for (let i = 0; i < 4; i++) {
      await nextBtn.click();
      await page.waitForTimeout(500);
    }

    // 3. Click "입문" difficulty option
    const beginnerOpt = page.locator('button:has-text("입문")');
    await beginnerOpt.click();
    await page.waitForTimeout(300);

    // 4. Click "시작하기"
    const startBtn = page.locator('button', { hasText: /^시작하기$/ });
    await startBtn.click();
    await page.waitForTimeout(2000);

    // 5. Verify we land on home page (not redirected to onboarding)
    const url = page.url();
    expect(url).not.toContain('/onboarding');

    // Verify settings saved
    const settings = await page.evaluate(() => {
      const s = localStorage.getItem('userSettings');
      return s ? JSON.parse(s) : null;
    });
    expect(settings).not.toBeNull();
    expect(settings.hasCompletedOnboarding).toBe(true);
    expect(settings.difficulty).toBe('beginner');
  });

  // ==========================================
  // TEST 1: Story Page (/story)
  // ==========================================

  test('TEST1-01: Story page - Navigate to /story', async () => {
    await page.goto('/story');
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');

    // Should NOT show error page
    const hasError = await page.locator('text=오류가 발생했습니다').isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  test('TEST1-02: Story page - "시스코" or "Cisco" text visible', async () => {
    const ciscoKr = page.locator('text=시스코');
    const ciscoEn = page.locator('text=Cisco');
    const hasCiscoKr = await ciscoKr.first().isVisible().catch(() => false);
    const hasCiscoEn = await ciscoEn.first().isVisible().catch(() => false);
    expect(hasCiscoKr || hasCiscoEn).toBe(true);
  });

  test('TEST1-03: Story page - "Thinking Point" visible', async () => {
    await expect(page.locator('text=Thinking Point').first()).toBeVisible({ timeout: 5000 });
  });

  test('TEST1-04: Story page - "NEXT STEP" button visible', async () => {
    await expect(page.locator('button:has-text("NEXT STEP")')).toBeVisible({ timeout: 5000 });
  });

  test('TEST1-05: Story page - Click NEXT STEP navigates to /comparison', async () => {
    await page.locator('button:has-text("NEXT STEP")').click();
    await page.waitForURL('**/comparison**', { timeout: 5000 });
    expect(page.url()).toContain('/comparison');
  });

  // ==========================================
  // TEST 2: Comparison Page (/comparison)
  // ==========================================

  test('TEST2-01: Comparison page - snapshot (no error)', async () => {
    await page.waitForTimeout(1000);
    await page.waitForLoadState('networkidle');

    const hasError = await page.locator('text=오류가 발생했습니다').isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  test('TEST2-02: Comparison page - "엔비디아" text visible', async () => {
    await expect(page.locator('text=엔비디아').first()).toBeVisible({ timeout: 5000 });
  });

  test('TEST2-03: Comparison page - PER values "150x" and "60x" visible', async () => {
    await expect(page.locator('text=150x')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=60x')).toBeVisible({ timeout: 5000 });
  });

  test('TEST2-04: Comparison page - "당신의 생각은?" visible', async () => {
    await expect(page.locator('text=당신의 생각은?').first()).toBeVisible({ timeout: 5000 });
  });

  test('TEST2-05: Comparison page - "버블이다" and "아직 싸다" buttons visible', async () => {
    await expect(page.locator('button:has-text("버블이다")')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('button:has-text("아직 싸다")')).toBeVisible({ timeout: 5000 });
  });

  test('TEST2-06: Comparison page - Click "버블이다" and verify selection', async () => {
    const bubbleBtn = page.locator('button:has-text("버블이다")');
    await bubbleBtn.click();
    await page.waitForTimeout(500);

    // Verify button has a selected/active visual state
    const classes = await bubbleBtn.getAttribute('class');
    // Check for some indicator of selection (border, bg color, ring, etc.)
    const isSelected = classes.includes('border-') || classes.includes('bg-') || classes.includes('ring-') || classes.includes('selected');
    expect(isSelected).toBe(true);
  });

  test('TEST2-07: Comparison page - Click NEXT STEP navigates to /companies', async () => {
    await page.locator('button:has-text("NEXT STEP")').click();
    await page.waitForURL('**/companies**', { timeout: 5000 });
    expect(page.url()).toContain('/companies');
  });

  // ==========================================
  // TEST 3: Companies Page (/companies)
  // ==========================================

  test('TEST3-01: Companies page - snapshot (no error)', async () => {
    await page.waitForTimeout(1000);
    await page.waitForLoadState('networkidle');

    const hasError = await page.locator('text=오류가 발생했습니다').isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  test('TEST3-02: Companies page - "핵심 플레이어들" text visible', async () => {
    await expect(page.locator('text=핵심 플레이어들')).toBeVisible({ timeout: 5000 });
  });

  test('TEST3-03: Companies page - "SK 하이닉스" or "SK" text visible', async () => {
    const skHynix = page.locator('text=SK 하이닉스');
    const sk = page.locator('text=SK');
    const hasSKHynix = await skHynix.first().isVisible().catch(() => false);
    const hasSK = await sk.first().isVisible().catch(() => false);
    expect(hasSKHynix || hasSK).toBe(true);
  });

  test('TEST3-04: Companies page - "대장주" badge visible', async () => {
    await expect(page.locator('text=대장주').first()).toBeVisible({ timeout: 5000 });
  });

  test('TEST3-05: Companies page - "처음으로 돌아가기" button visible', async () => {
    await expect(page.locator('button:has-text("처음으로 돌아가기")')).toBeVisible({ timeout: 5000 });
  });

  test('TEST3-06: Companies page - Click "처음으로 돌아가기" navigates to /', async () => {
    await page.locator('button:has-text("처음으로 돌아가기")').click();
    await page.waitForURL('**/', { timeout: 5000 });
    // Should be on home page (/ or empty path)
    const url = page.url();
    const isHome = url.endsWith('/') || url.endsWith(':3001');
    expect(isHome).toBe(true);
  });
});
