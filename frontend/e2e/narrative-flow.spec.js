// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
};

test.describe('내러티브 6단계 플로우 (FE-NARR)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/narrative?keyword=바이오&caseId=6&syncRate=80');
    // STEP 1이 로드될 때까지 대기
    await expect(page.getByText('STEP 1')).toBeVisible({ timeout: TIMEOUT.network });
  });

  test('FE-NARR-01: Step 1에서 KEY TAKEAWAYS가 표시된다', async ({ page }) => {
    await expect(page.getByText('KEY TAKEAWAYS')).toBeVisible({ timeout: TIMEOUT.fast });
  });

  test('FE-NARR-02: 다음 버튼으로 Step 2~6을 네비게이션할 수 있다', async ({ page }) => {
    for (let step = 2; step <= 6; step++) {
      await page.getByRole('button', { name: '다음' }).click();
      await expect(page.getByText(`STEP ${step}`)).toBeVisible({ timeout: TIMEOUT.fast });
    }
  });

  test('FE-NARR-03: 마지막 스텝에서 완료 버튼 클릭 시 홈으로 이동한다', async ({ page }) => {
    // Step 6까지 이동
    for (let i = 0; i < 5; i++) {
      await page.getByRole('button', { name: '다음' }).click();
      await page.waitForTimeout(300);
    }
    // 완료 버튼 클릭 후 홈 이동 확인
    await page.getByRole('button', { name: '완료' }).click();
    await expect(page).toHaveURL(/\/$/, { timeout: TIMEOUT.network });
  });
});
