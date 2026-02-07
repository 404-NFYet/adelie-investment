// @ts-check
import { test, expect } from '@playwright/test';

test.describe('내러티브 6단계 플로우', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/narrative?keyword=바이오&caseId=6&syncRate=80');
    // STEP 1이 로드될 때까지 대기
    await expect(page.locator('text=STEP 1')).toBeVisible({ timeout: 10000 });
  });

  test('Step 1에서 KEY TAKEAWAYS가 표시된다', async ({ page }) => {
    await expect(page.locator('text=KEY TAKEAWAYS')).toBeVisible();
  });

  test('다음 버튼으로 Step 2~6을 네비게이션할 수 있다', async ({ page }) => {
    for (let step = 2; step <= 6; step++) {
      await page.locator('button:has-text("다음")').click();
      await expect(page.locator(`text=STEP ${step}`)).toBeVisible({ timeout: 3000 });
    }
  });

  test('마지막 스텝에서 완료 버튼을 클릭하면 홈으로 이동한다', async ({ page }) => {
    // Step 6까지 이동
    for (let i = 0; i < 5; i++) {
      await page.locator('button:has-text("다음")').click();
      await page.waitForTimeout(500);
    }
    // 완료 버튼 클릭
    await page.locator('button:has-text("완료")').click();
    await expect(page).toHaveURL('/', { timeout: 3000 });
  });
});
