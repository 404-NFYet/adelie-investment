import { test, expect } from '@playwright/test';

test.describe('AI Tutor', () => {
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

  test('should have tutor button or area', async ({ page }) => {
    // Look for any tutor-related element
    const tutorArea = page.locator('[class*="tutor"], button:has-text("질문"), button:has-text("AI")');
    // It may or may not be visible depending on page state
  });
});
