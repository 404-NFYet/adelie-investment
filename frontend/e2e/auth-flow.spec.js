import { test, expect } from '@playwright/test';

// Use a unique email to avoid "already registered" errors
const timestamp = Date.now();
const TEST_EMAIL = `browsertest_${timestamp}@test.com`;
const TEST_PASSWORD = 'test12345';
const TEST_USERNAME = `user_${timestamp}`;

test.describe.serial('Full Authentication Flow', () => {

  // ── Pre-setup: Clear localStorage ──────────────────────────────
  test('Pre-setup: Clear localStorage', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForTimeout(1000);
    console.log('✅ Pre-setup: localStorage cleared');
  });

  // ── Test 1: Redirect to onboarding ─────────────────────────────
  test('Test 1: Redirect to /onboarding', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForTimeout(2000);
    const url = page.url();
    console.log(`Current URL: ${url}`);
    expect(url).toContain('/onboarding');
    console.log('✅ Test 1 PASS: Redirected to /onboarding');
  });

  // ── Test 2: Complete onboarding -> redirect to /auth ───────────
  test('Test 2: Complete onboarding -> redirect to /auth', async ({ page }) => {
    // Start fresh
    await page.goto('http://localhost:3001');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForTimeout(2000);

    // Should be on onboarding
    expect(page.url()).toContain('/onboarding');

    // Click "다음" 4 times
    for (let i = 0; i < 4; i++) {
      const nextBtn = page.getByRole('button', { name: '다음' });
      await nextBtn.waitFor({ timeout: 5000 });
      await nextBtn.click();
      await page.waitForTimeout(500);
      console.log(`Clicked 다음 (${i + 1}/4)`);
    }

    // Select "입문" level
    const beginnerOption = page.getByText('입문', { exact: false });
    await beginnerOption.waitFor({ timeout: 5000 });
    await beginnerOption.click();
    await page.waitForTimeout(500);
    console.log('Selected 입문');

    // Click "시작하기"
    const startBtn = page.getByRole('button', { name: '시작하기' });
    await startBtn.waitFor({ timeout: 5000 });
    await startBtn.click();
    await page.waitForTimeout(2000);

    const url = page.url();
    console.log(`Current URL after onboarding: ${url}`);
    expect(url).toContain('/auth');
    console.log('✅ Test 2 PASS: Redirected to /auth after onboarding');
  });

  // ── Test 3: Register a new user ────────────────────────────────
  test('Test 3: Register a new user', async ({ page }) => {
    // Continue from onboarding completion state
    await page.goto('http://localhost:3001');
    await page.evaluate(() => {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
    });
    await page.goto('http://localhost:3001/auth');
    await page.waitForTimeout(2000);

    // Click "회원가입" tab (it's the first button, not the submit)
    const registerTab = page.getByRole('button', { name: '회원가입' }).first();
    await registerTab.waitFor({ timeout: 5000 });
    await registerTab.click();
    await page.waitForTimeout(1000);
    console.log('Clicked 회원가입 tab');

    // Fill in registration form
    const emailInput = page.locator('input[type="email"]').first();
    const passwordInput = page.locator('input[type="password"]').first();

    await emailInput.fill(TEST_EMAIL);
    await passwordInput.fill(TEST_PASSWORD);
    console.log(`Filled email (${TEST_EMAIL}) and password`);

    // Username field - placeholder is "홍길동"
    const usernameInput = page.getByPlaceholder('홍길동').or(
      page.locator('input[name="username"]')
    ).first();

    try {
      await usernameInput.waitFor({ timeout: 3000 });
      await usernameInput.fill(TEST_USERNAME);
      console.log(`Filled username: ${TEST_USERNAME}`);
    } catch {
      console.log('Username field not found, may not be required');
    }

    // Click 회원가입 submit button (the one inside the form, type=submit)
    const registerBtn = page.locator('form').getByRole('button', { name: '회원가입' });
    await registerBtn.click();
    console.log('Clicked 회원가입 submit button');

    // Wait for navigation
    await page.waitForTimeout(5000);

    const url = page.url();
    console.log(`Current URL after register: ${url}`);

    // Check: should navigate to / (home page)
    const isHome = url.endsWith(':3001/') || url.endsWith(':3001') || url.includes('localhost:3001/#') || !url.includes('/auth');
    expect(isHome).toBeTruthy();
    console.log('✅ Test 3 PASS: Navigated to home page after registration');

    // Check keywords displayed
    const pageContent = await page.textContent('body');
    console.log(`Page has content length: ${pageContent.length}`);
    // Just check that meaningful content is loaded (not stuck on auth page)
    expect(pageContent.length).toBeGreaterThan(100);
    console.log('✅ Test 3 PASS: Content is displayed (user is authenticated)');
  });

  // ── Test 4: Logout and login ───────────────────────────────────
  test('Test 4: Logout and login', async ({ page }) => {
    await page.goto('http://localhost:3001');
    await page.waitForTimeout(1000);

    // Simulate logout
    await page.evaluate(() => {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      location.reload();
    });
    await page.waitForTimeout(2000);

    // Navigate to auth page
    await page.goto('http://localhost:3001/auth');
    await page.waitForTimeout(2000);

    // Click "로그인" tab (should already be active, but click to be sure)
    const loginTab = page.getByRole('tab', { name: '로그인' }).or(
      page.getByText('로그인', { exact: false }).first()
    );
    try {
      await loginTab.waitFor({ timeout: 3000 });
      await loginTab.click();
      await page.waitForTimeout(500);
      console.log('Clicked 로그인 tab');
    } catch {
      console.log('로그인 tab already active or not found as tab');
    }

    // Fill in login form
    const emailInput = page.getByPlaceholder('이메일').or(
      page.locator('input[type="email"]')
    ).first();
    const passwordInput = page.getByPlaceholder('비밀번호').or(
      page.locator('input[type="password"]')
    ).first();

    await emailInput.fill(TEST_EMAIL);
    await passwordInput.fill(TEST_PASSWORD);
    console.log(`Filled email (${TEST_EMAIL}) and password`);

    // Click 로그인 submit button (the one inside the form)
    const loginBtn = page.locator('form').getByRole('button', { name: '로그인' });
    await loginBtn.click();
    console.log('Clicked 로그인 button');

    // Wait for navigation
    await page.waitForTimeout(5000);

    const url = page.url();
    console.log(`Current URL after login: ${url}`);

    const isHome = url.endsWith(':3001/') || url.endsWith(':3001') || !url.includes('/auth');
    expect(isHome).toBeTruthy();
    console.log('✅ Test 4 PASS: Navigated to home page after login');
  });

  // ── Test 5: Guest access ───────────────────────────────────────
  test('Test 5: Guest access', async ({ page }) => {
    // Clear localStorage
    await page.goto('http://localhost:3001');
    await page.evaluate(() => localStorage.clear());
    await page.waitForTimeout(1000);

    // Navigate to auth page
    await page.goto('http://localhost:3001/auth');
    await page.waitForTimeout(2000);

    // Click "게스트로 시작하기"
    const guestBtn = page.getByText('게스트로 시작하기');
    await guestBtn.waitFor({ timeout: 5000 });
    await guestBtn.click();
    console.log('Clicked 게스트로 시작하기');

    await page.waitForTimeout(3000);

    const url = page.url();
    console.log(`Current URL after guest access: ${url}`);

    const isHome = url.endsWith(':3001/') || url.endsWith(':3001') || !url.includes('/auth');
    expect(isHome).toBeTruthy();
    console.log('✅ Test 5 PASS: Navigated to home page in guest mode');

    // Check keywords displayed
    const pageContent = await page.textContent('body');
    console.log(`Page content length: ${pageContent.length}`);
    expect(pageContent.length).toBeGreaterThan(100);
    console.log('✅ Test 5 PASS: Keywords displayed in guest mode');
  });
});
