import { test, expect } from '@playwright/test';

test.describe('Onboarding Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test('should show onboarding for new users', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/onboarding/);
  });

  test('should display logo or title', async ({ page }) => {
    await page.goto('/onboarding');
    const title = page.locator('h1, .logo, [class*="logo"]');
    await expect(title.first()).toBeVisible({ timeout: 5000 });
  });

  test('should allow difficulty selection', async ({ page }) => {
    await page.goto('/onboarding');
    const beginnerOption = page.getByText(/입문|beginner/i);
    await expect(beginnerOption.first()).toBeVisible({ timeout: 5000 });
  });
});
