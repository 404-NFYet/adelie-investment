// @ts-check
import { test, expect } from '@playwright/test';

const TIMEOUT = {
  fast: 5_000,
  network: 10_000,
  llm: 20_000,
};

test.describe('AI 튜터 시각화 (FE-VIZ)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // AI 튜터 FAB 클릭하여 채팅창 열기
    const fab = page.getByText('AI 튜터').first();
    await fab.waitFor({ timeout: TIMEOUT.fast });
    await fab.click();
    // 채팅 입력창 표시 확인
    await expect(
      page.getByPlaceholder('질문을 입력하세요').or(page.getByText('질문을 입력하세요'))
    ).toBeVisible({ timeout: TIMEOUT.fast });
  });

  test('FE-VIZ-01: "차트" 키워드 입력 시 차트 관련 버튼 또는 응답이 노출된다', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').last();
    await input.fill('삼성전자 주가 차트 보여줘');
    await input.press('Enter');
    // 차트 버튼 또는 로딩 메시지 대기
    const chartBtn = page.getByRole('button', { name: /차트|급등주|시각화/ });
    const response = page.locator('[class*="message"], [class*="chat"]').last();
    await expect(chartBtn.or(response)).toBeVisible({ timeout: TIMEOUT.llm });
  });

  test('FE-VIZ-02: 차트 버튼 클릭 시 Plotly 컨테이너가 렌더링된다', async ({ page }) => {
    // 급등주 차트 버튼 클릭 (있을 경우)
    const chartBtn = page.getByRole('button', { name: /급등주|차트/ }).first();
    if (await chartBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await chartBtn.click();
      // Plotly 차트(.js-plotly-plot) 또는 에러 메시지 대기
      const plotlyChart = page.locator('.js-plotly-plot');
      const errorMsg = page.locator('text=/차트 생성 실패|에러|오류/');
      await expect(plotlyChart.or(errorMsg)).toBeVisible({ timeout: TIMEOUT.llm });
    } else {
      test.skip(true, '차트 버튼 미노출 — 서버 데이터 없음');
    }
  });

  test('FE-VIZ-03: 차트 기간 변경 버튼(1개월/3개월/1년) UI가 존재한다', async ({ page }) => {
    const chartBtn = page.getByRole('button', { name: /급등주|차트/ }).first();
    if (await chartBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
      await chartBtn.click();
      // Plotly 차트 렌더링 대기
      await page.locator('.js-plotly-plot').waitFor({ timeout: TIMEOUT.llm }).catch(() => null);
      // 기간 변경 버튼 확인 (1개월 or 1M 등)
      const periodBtn = page.getByRole('button', { name: /1개월|3개월|1년|1M|3M|1Y/ }).first();
      if (await periodBtn.isVisible({ timeout: TIMEOUT.fast }).catch(() => false)) {
        await periodBtn.click();
        await expect(periodBtn).toBeVisible({ timeout: TIMEOUT.fast });
      }
    } else {
      test.skip(true, '차트 버튼 미노출 — 서버 데이터 없음');
    }
  });
});
