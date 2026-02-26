import { test } from '@playwright/test';

const BASE = process.env.BASE_URL || 'https://demo.adelie-invest.com';
const E2E_EMAIL = process.env.E2E_EMAIL || 'test0208@gmail.com';
const E2E_PASSWORD = process.env.E2E_PASSWORD || 'test1234';
const STEP_KEYS = ['background', 'concept_explain', 'history', 'application', 'caution', 'summary'];

test('오늘 케이스 내러티브 전체 스텝 스크린샷', async ({ page, request }, testInfo) => {
  const device = testInfo.project.name.replace(/\s/g, '-').toLowerCase(); // 'galaxy-s25' | 'iphone-12'

  // 1) /auth 페이지에서 실제 로그인 (쿠키 기반 인증)
  await page.goto(`${BASE}/auth`);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);

  // 이메일/비밀번호 입력 후 로그인
  await page.fill('input[type="email"]', E2E_EMAIL);
  await page.fill('input[type="password"]', E2E_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);

  console.log(`[${device}] 로그인 완료. 현재 URL: ${page.url()}`);

  // 2) 오늘 케이스 ID 수집
  const res = await request.get(`${BASE}/api/v1/keywords/today`);
  const data = await res.json();
  const cases = (data.keywords || [])
    .filter(k => k.case_id)
    .map(k => ({ caseId: k.case_id, title: k.title }));

  console.log(`[${device}] 오늘 케이스: ${cases.length}개`);

  // 3) 각 케이스 6스텝 전체 캡처
  for (const { caseId, title } of cases) {
    console.log(`\n--- [${device}] case ${caseId}: ${title} ---`);

    await page.goto(`${BASE}/narrative/${caseId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    for (let i = 0; i < 6; i++) {
      await page.screenshot({
        path: `e2e/screenshots/today-${device}-c${caseId}-s${i + 1}-${STEP_KEYS[i]}.png`,
        fullPage: true,
      });
      console.log(`  step ${i + 1}/${STEP_KEYS[i]} 캡처`);

      if (i < 5) {
        const nextBtn = page.locator('button:has-text("다음")');
        await nextBtn.scrollIntoViewIfNeeded();
        await nextBtn.click();
        await page.waitForTimeout(600);
      }
    }
  }
});
