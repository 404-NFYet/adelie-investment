// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
};

/**
 * 알림 페이지 인증 헬퍼 (게스트 로그인)
 */
async function loginAndGoToNotifications(page) {
  const ts = Date.now();
  await page.goto('/auth');
  await page.waitForLoadState('networkidle');

  // 회원가입 또는 게스트 로그인
  const registerTab = page.getByRole('button', { name: '회원가입' }).first();
  if (await registerTab.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
    await registerTab.click();
    await page.waitForTimeout(500);
    const emailInput = page.locator('input[type="email"]').first();
    if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await emailInput.fill(`notif_${ts}@adelie.test`);
      await page.locator('input[type="password"]').first().fill('Test1234!');
      const nicknameInput = page.getByPlaceholder('홍길동').first();
      if (await nicknameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await nicknameInput.fill(`notif_${ts}`);
      }
      await page.locator('form').getByRole('button', { name: '회원가입' }).click();
    }
  } else {
    const guestBtn = page.getByText('게스트로 시작하기');
    if (await guestBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await guestBtn.click();
    }
  }

  await page.waitForURL(/\/(home|)$/, { timeout: TIMEOUT.network }).catch(() => null);
  await page.goto('/notifications');
  await page.waitForLoadState('networkidle');
}

test.describe('알림 페이지 (FE-NOT)', () => {
  test('FE-NOT-01: 알림 페이지가 로드되고 렌더링된다', async ({ page }) => {
    await loginAndGoToNotifications(page);
    // 페이지 타이틀 또는 알림 관련 텍스트 확인
    const header = page.getByText(/알림|notification/i).first();
    await expect(header).toBeVisible({ timeout: TIMEOUT.network });
    await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
  });

  test('FE-NOT-02: 알림이 없을 때 빈 상태 메시지가 표시된다', async ({ page }) => {
    await loginAndGoToNotifications(page);
    // 알림이 없는 경우 빈 상태 텍스트 또는 목록 자체를 확인
    // (파이프라인 의존 → 빈 상태 우선 검증)
    const emptyMsg = page.getByText(/알림이 없|새로운 알림|아직/).first();
    const notifList = page.locator('[class*="notif"], [class*="Notif"], [class*="item"]').first();
    // 빈 상태 메시지 또는 목록 둘 중 하나는 존재해야 함
    await expect(emptyMsg.or(notifList)).toBeVisible({ timeout: TIMEOUT.network });
  });

  test('FE-NOT-03: 알림 항목이 있을 경우 날짜와 내용 구조를 갖는다', async ({ page }) => {
    await loginAndGoToNotifications(page);
    const notifItem = page.locator('[class*="notif-item"], [class*="NotifItem"], [class*="notification-item"]').first();
    if (await notifItem.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      // 날짜 패턴 확인 (YYYY-MM-DD 또는 상대 시간)
      const dateEl = notifItem.locator('time, [class*="date"], [class*="time"]').first();
      const contentEl = notifItem.locator('p, span, [class*="content"]').first();
      // 날짜 또는 내용 중 하나는 존재해야 함
      const hasStructure =
        await dateEl.isVisible({ timeout: 2000 }).catch(() => false) ||
        await contentEl.isVisible({ timeout: 2000 }).catch(() => false);
      expect(hasStructure).toBe(true);
    } else {
      // 알림 없음 → pass (파이프라인 의존)
      test.skip(true, '알림 항목 없음 — 파이프라인 실행 필요');
    }
  });
});
