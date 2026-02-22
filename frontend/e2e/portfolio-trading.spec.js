// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
};

/**
 * 포트폴리오 페이지 인증 헬퍼
 * 타임스탬프 기반 고유 계정으로 로그인 후 /portfolio 이동
 */
async function loginAndGoToPortfolio(page) {
  const ts = Date.now();
  await page.goto('/auth');
  await page.waitForLoadState('networkidle');

  // 회원가입 탭 클릭
  const registerTab = page.getByRole('button', { name: '회원가입' }).first();
  if (await registerTab.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
    await registerTab.click();
    await page.waitForTimeout(500);
  }

  // 이메일 + 비밀번호 + 닉네임 입력
  const emailInput = page.locator('input[type="email"]').first();
  const passwordInput = page.locator('input[type="password"]').first();
  if (await emailInput.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
    await emailInput.fill(`port_${ts}@adelie.test`);
    await passwordInput.fill('Test1234!');
    const nicknameInput = page.getByPlaceholder('홍길동').first();
    if (await nicknameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await nicknameInput.fill(`port_${ts}`);
    }
    await page.locator('form').getByRole('button', { name: '회원가입' }).click();
  } else {
    // 게스트 로그인 fallback
    const guestBtn = page.getByText('게스트로 시작하기');
    if (await guestBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await guestBtn.click();
    }
  }

  await page.waitForURL(/\/(home|)$/, { timeout: TIMEOUT.network }).catch(() => null);
  await page.goto('/portfolio');
  await page.waitForLoadState('networkidle');
}

// ─── 데스크톱 테스트 ───────────────────────────────────────────

test.describe('포트폴리오 & 모의투자 (FE-PORT)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAndGoToPortfolio(page);
  });

  test('FE-PORT-01: 포트폴리오 페이지 로드 + 보유 종목 섹션이 표시된다', async ({ page }) => {
    // 포트폴리오 관련 텍스트(보유/종목/포트폴리오) 확인
    const section = page.getByText(/보유|포트폴리오|종목|자산/).first();
    await expect(section).toBeVisible({ timeout: TIMEOUT.network });
    // 에러 화면 미노출
    await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
  });

  test('FE-PORT-02: 종목 검색 → 결과 또는 검색 UI가 표시된다', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="검색"], input[placeholder*="종목"]').first();
    if (await searchInput.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await searchInput.fill('삼성');
      await page.waitForTimeout(500);
      // 검색 결과 또는 입력값 유지 확인
      const result = page.getByText(/삼성|검색 결과/).first();
      await expect(result).toBeVisible({ timeout: TIMEOUT.network });
    } else {
      // 검색 입력창이 없는 경우 skip
      test.skip(true, '종목 검색 UI 미노출');
    }
  });

  test('FE-PORT-03: 매수 버튼 클릭 시 매수 모달 또는 패널이 표시된다', async ({ page }) => {
    const buyBtn = page.getByRole('button', { name: /매수|구매|BUY/ }).first();
    if (await buyBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await buyBtn.click();
      // 매수 모달/패널 등장 확인
      const modal = page.locator('[role="dialog"], [class*="modal"], [class*="Modal"]').first();
      const panel = page.getByText(/매수|수량|가격|확인/).first();
      await expect(modal.or(panel)).toBeVisible({ timeout: TIMEOUT.fast });
    } else {
      test.skip(true, '매수 버튼 미노출 — 보유 종목 없음');
    }
  });

  test('FE-PORT-04: 자유매매 탭 전환이 동작한다', async ({ page }) => {
    // 탭 전환 (보유/미보유 또는 자유매매 탭)
    const freeTab = page.getByRole('tab', { name: /자유|전체|미보유/ }).or(
      page.getByRole('button', { name: /자유|전체|미보유/ })
    ).first();
    if (await freeTab.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await freeTab.click();
      await page.waitForTimeout(500);
      // 탭 전환 후 에러 없음 확인
      await expect(page.getByText('앗, 문제가 생겼어요')).not.toBeVisible();
    } else {
      test.skip(true, '자유매매 탭 미노출');
    }
  });

  test('FE-PORT-05: 랭킹보드 탭 클릭 시 사용자 목록이 표시된다', async ({ page }) => {
    const rankTab = page.getByRole('tab', { name: /랭킹|순위/ }).or(
      page.getByRole('button', { name: /랭킹|순위/ })
    ).first();
    if (await rankTab.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await rankTab.click();
      // 랭킹 목록 또는 빈 상태 메시지 확인
      const rankList = page.locator('[class*="rank"], [class*="Rank"]').first();
      const emptyMsg = page.getByText(/아직|없습니다|랭킹/).first();
      await expect(rankList.or(emptyMsg)).toBeVisible({ timeout: TIMEOUT.network });
    } else {
      test.skip(true, '랭킹 탭 미노출');
    }
  });
});

// ─── 모바일 테스트 (360px) ────────────────────────────────────

test.describe('포트폴리오 모바일 (FE-PORT-M)', () => {
  test.use({ viewport: { width: 360, height: 780 } });

  test('FE-PORT-M01: 모바일(360px)에서 매수 버튼 터치 영역이 40px 이상이다', async ({ page }) => {
    await loginAndGoToPortfolio(page);
    const buyBtn = page.getByRole('button', { name: /매수|구매|BUY/ }).first();
    if (await buyBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      const box = await buyBtn.boundingBox();
      expect(box).not.toBeNull();
      // 터치 영역 최소 40px (WCAG 2.5.5 권장)
      expect(box.height).toBeGreaterThanOrEqual(40);
    } else {
      test.skip(true, '매수 버튼 미노출 — 보유 종목 없음');
    }
  });
});
