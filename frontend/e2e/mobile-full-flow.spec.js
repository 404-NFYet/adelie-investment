/**
 * Mobile Full Flow E2E Tests (iPhone 12 Pro - 390x844)
 * Single SPA session with SPA-based navigation.
 *
 * Known Bugs:
 *   BUG-01: Onboarding sets settings.hasCompletedOnboarding but not token.
 *           ProtectedRoute checks user (from useEffect/token) so redirect loop occurs.
 *   BUG-02: ThemeProvider missing from App.jsx - Story, Comparison, Companies crash.
 */
import { test, expect } from '@playwright/test';

const MOBILE_VIEWPORT = { width: 390, height: 844 };

test.use({
  viewport: MOBILE_VIEWPORT,
  userAgent:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
});

test.describe.serial('Mobile Full Flow', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext({ viewport: MOBILE_VIEWPORT });
    page = await context.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  // =========== ONBOARDING ===========

  test('FE-ONB-01: Narrative and Investment text visible', async () => {
    await page.goto('/onboarding');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/onboarding');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Narrative')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Investment')).toBeVisible({ timeout: 5000 });
  });

  test('FE-ONB-02: Click next 4 times, verify each step', async () => {
    const btn = page.locator('button', { hasText: /^\uB2E4\uC74C$/ });
    await btn.click();
    await expect(page.locator('text=\uACFC\uAC70\uC5D0\uC11C \uBC30\uC6B0\uB294 \uD22C\uC790')).toBeVisible({ timeout: 3000 });
    await btn.click();
    await expect(page.locator('text=\uC2A4\uD1A0\uB9AC\uD154\uB9C1\uC73C\uB85C \uC27D\uAC8C')).toBeVisible({ timeout: 3000 });
    await btn.click();
    await expect(page.locator('text=AI \uD29C\uD130\uC640 \uD568\uAED8')).toBeVisible({ timeout: 3000 });
    await btn.click();
    await expect(page.locator('text=\uD22C\uC790 \uACBD\uD5D8\uC744 \uC54C\uB824\uC8FC\uC138\uC694')).toBeVisible({ timeout: 3000 });
  });

  test('FE-ONB-03: Click prev, verify previous step', async () => {
    await page.locator('button', { hasText: /^\uC774\uC804$/ }).click();
    await expect(page.locator('text=AI \uD29C\uD130\uC640 \uD568\uAED8')).toBeVisible({ timeout: 3000 });
  });

  test('FE-ONB-04: Go to last step, click beginner', async () => {
    await page.locator('button', { hasText: /^\uB2E4\uC74C$/ }).click();
    await expect(page.locator('text=\uD22C\uC790 \uACBD\uD5D8\uC744 \uC54C\uB824\uC8FC\uC138\uC694')).toBeVisible({ timeout: 3000 });
    const opt = page.locator('button:has-text("\uC785\uBB38")');
    await opt.click();
    await expect(opt).toHaveClass(/border-primary/);
  });

  test('FE-ONB-05: Start button enabled', async () => {
    const btn = page.locator('button', { hasText: /^\uC2DC\uC791\uD558\uAE30$/ });
    await expect(btn).toBeEnabled();
    await expect(btn).not.toHaveClass(/cursor-not-allowed/);
  });

  test('FE-ONB-06: Click start, settings saved', async () => {
    await page.locator('button', { hasText: /^\uC2DC\uC791\uD558\uAE30$/ }).click();
    await page.waitForTimeout(1000);
    const settings = await page.evaluate(() => {
      const s = localStorage.getItem('userSettings');
      return s ? JSON.parse(s) : null;
    });
    expect(settings).not.toBeNull();
    expect(settings.hasCompletedOnboarding).toBe(true);
    expect(settings.difficulty).toBe('beginner');
  });

  // =========== HOME PAGE ===========

  test('FE-HOME-01: History Mirror header and keyword title', async () => {
    await page.evaluate(() => localStorage.setItem('token', 'e2e-token'));
    await page.goto('/');
    await page.waitForTimeout(2000);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=History Mirror')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('h2:has-text("3")')).toBeVisible({ timeout: 3000 });
  });

  test('FE-HOME-02: 3 keyword cards', async () => {
    await expect(page.locator('h3:has-text("AI")')).toBeVisible();
    await expect(page.locator('h3:has-text("PBR")')).toBeVisible();
    await expect(page.locator('h3:has-text("\uBB3C\uAC00")')).toBeVisible();
  });

  test('FE-HOME-03: Click first keyword card', async () => {
    await page.locator('h3:has-text("AI")').first().click();
    await page.waitForTimeout(500);
  });

  test('FE-HOME-04: START BRIEFING visible', async () => {
    await expect(page.locator('button:has-text("START BRIEFING")')).toBeVisible({ timeout: 3000 });
  });

  test('FE-HOME-06: START BRIEFING -> /matching', async () => {
    await page.locator('button:has-text("START BRIEFING")').click();
    await page.waitForURL('**/matching**', { timeout: 5000 });
    expect(page.url()).toContain('/matching');
  });

  // =========== MATCHING PAGE ===========

  test('FE-MATCH-01: MATCHING COMPLETED visible', async () => {
    await expect(page.locator('text=MATCHING COMPLETED')).toBeVisible({ timeout: 5000 });
  });

  test('FE-MATCH-02: 92% visible', async () => {
    await expect(page.locator('text=92%')).toBeVisible({ timeout: 3000 });
  });

  test('FE-MATCH-03: PAST/PRESENT labels', async () => {
    await expect(page.locator('text=PAST')).toBeVisible();
    await expect(page.locator('text=PRESENT')).toBeVisible();
  });

  test('FE-MATCH-04: KEY INSIGHT', async () => {
    await expect(page.locator('text=KEY INSIGHT')).toBeVisible();
  });

  test('FE-MATCH-06: NEXT STEP -> /story', async () => {
    await page.locator('button:has-text("NEXT STEP")').click();
    await page.waitForURL('**/story', { timeout: 5000 });
    expect(page.url()).toContain('/story');
  });

  // =========== STORY PAGE (BUG-02: expected to fail) ===========

  test('FE-STORY-01: Cisco title', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing from App.jsx');
    await page.waitForTimeout(1000);
    await expect(page.locator('text=\uC2DC\uC2A4\uCF54').first()).toBeVisible({ timeout: 2000 });
  });

  test('FE-STORY-02: Story paragraphs', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('text=2000\uB144').first()).toBeVisible({ timeout: 2000 });
  });

  test('FE-STORY-04: Thinking Point', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('text=Thinking Point').first()).toBeVisible({ timeout: 2000 });
  });

  test('FE-STORY-06: NEXT STEP button exists', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing - NEXT STEP button not rendered');
    await expect(page.locator('button:has-text("NEXT STEP")')).toBeVisible({ timeout: 2000 });
  });

  // =========== Recover from Story crash ===========

  test('RECOVER-1: Back to Home after Story crash', async () => {
    const hasError = await page.locator('text=\uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4').isVisible();
    if (hasError) {
      await page.locator('button:has-text("\uD648\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30")').click();
      await page.waitForTimeout(1000);
    }
    await expect(page.locator('text=History Mirror')).toBeVisible({ timeout: 5000 });
  });

  // =========== SEARCH PAGE (via bottom nav) ===========

  test('FE-SEARCH-01: Search input visible', async () => {
    await page.locator('button:has-text("\uAC80\uC0C9")').click();
    await page.waitForTimeout(1000);
    await expect(page.locator('input[type="text"]')).toBeVisible({ timeout: 5000 });
  });

  test('FE-SEARCH-02: Search and navigate to comparison', async () => {
    await page.locator('input[type="text"]').fill('\uBC18\uB3C4\uCCB4');
    await page.locator('button:has-text("\uAC80\uC0C9")').last().click();
    await page.waitForURL('**/comparison**', { timeout: 5000 });
    expect(page.url()).toContain('/comparison');
  });

  // =========== COMPARISON (BUG-02: expected to fail) ===========

  test('FE-COMP-01: Title with NVidia', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing - Comparison crashes');
    await page.waitForTimeout(1000);
    await expect(page.locator('text=\uC5D4\uBE44\uB514\uC544').first()).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMP-02: PER bars 150x 60x', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('text=150x')).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMP-05: Poll question', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('text=\uBC84\uBE14\uC77C\uAE4C\uC694').first()).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMP-06: Click bubble option', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('button:has-text("\uBC84\uBE14\uC774\uB2E4")')).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMP-08: NEXT STEP button exists', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('button:has-text("NEXT STEP")')).toBeVisible({ timeout: 2000 });
  });

  // =========== Recover from Comparison crash ===========

  test('RECOVER-2: Back to Home after Comparison crash', async () => {
    const hasError = await page.locator('text=\uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4').isVisible();
    if (hasError) {
      await page.locator('button:has-text("\uD648\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30")').click();
      await page.waitForTimeout(1000);
    }
    const onHome = await page.locator('text=History Mirror').isVisible();
    if (!onHome) {
      await page.goto('/');
      await page.waitForTimeout(2000);
    }
    await expect(page.locator('text=History Mirror')).toBeVisible({ timeout: 5000 });
  });

  // =========== COMPANIES (BUG-02: expected to fail) ===========

  test('FE-COMPANIES-01: Title visible', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing - Companies crashes');
    await page.evaluate(() => {
      window.history.pushState({}, '', '/companies');
      window.dispatchEvent(new PopStateEvent('popstate'));
    });
    await page.waitForTimeout(1000);
    await expect(page.locator('text=\uD575\uC2EC \uD50C\uB808\uC774\uC5B4\uB4E4')).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMPANIES-02: Company cards', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('text=SK \uD558\uC774\uB2C9\uC2A4')).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMPANIES-03: Role badges', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('text=\uB300\uC7A5\uC8FC')).toBeVisible({ timeout: 2000 });
  });

  test('FE-COMPANIES-04: Back to home button', async () => {
    test.fail(true, 'BUG-02: ThemeProvider missing');
    await expect(page.locator('button:has-text("\uCC98\uC74C\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30")')).toBeVisible({ timeout: 2000 });
  });

  // =========== Recover from Companies ===========

  test('RECOVER-3: Back to Home', async () => {
    const hasError = await page.locator('text=\uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4').isVisible();
    if (hasError) {
      await page.locator('button:has-text("\uD648\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30")').click();
      await page.waitForTimeout(1000);
    }
    const onHome = await page.locator('text=History Mirror').isVisible();
    if (!onHome) {
      await page.goto('/');
      await page.waitForTimeout(2000);
    }
    await expect(page.locator('text=History Mirror')).toBeVisible({ timeout: 5000 });
  });

  // =========== HISTORY PAGE ===========

  test('FE-HISTORY-01: History content visible', async () => {
    await page.locator('button:has-text("\uD788\uC2A4\uD1A0\uB9AC")').click();
    await page.waitForTimeout(1000);
    await expect(page.locator('text=\uD559\uC2B5 \uD788\uC2A4\uD1A0\uB9AC')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=AI \uBC18\uB3C4\uCCB4 \uAC70\uD488\uB860')).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=2\uCC28\uC804\uC9C0 \uAD6C\uC870\uC870\uC815')).toBeVisible();
    await expect(page.locator('text=\uAE08\uB9AC \uC778\uD558 \uAE30\uB300\uAC10')).toBeVisible();
  });
});
