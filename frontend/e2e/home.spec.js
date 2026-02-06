import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('narrative_user_settings', JSON.stringify({
        difficulty: 'beginner',
        hasCompletedOnboarding: true
      }));
    });
    await page.goto('/');
  });

  test('should display home page content', async ({ page }) => {
    const heading = page.locator('h1, h2, [class*="title"]');
    await expect(heading.first()).toBeVisible({ timeout: 10000 });
  });

  test('should have navigation', async ({ page }) => {
    const nav = page.locator('nav, [class*="nav"]');
    await expect(nav.first()).toBeVisible({ timeout: 5000 });
  });
});
