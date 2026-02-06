import { test, expect } from '@playwright/test';

test.describe('Search Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('narrative_user_settings', JSON.stringify({
        difficulty: 'beginner',
        hasCompletedOnboarding: true
      }));
    });
    await page.goto('/search');
  });

  test('should display search page', async ({ page }) => {
    const searchInput = page.getByRole('textbox').first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
  });

  test('should accept text input', async ({ page }) => {
    const searchInput = page.getByRole('textbox').first();
    await searchInput.fill('반도체');
    await expect(searchInput).toHaveValue('반도체');
  });
});
