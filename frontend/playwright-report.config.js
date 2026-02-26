import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: {
    baseURL: process.env.BASE_URL || 'https://demo.adelie-invest.com',
    headless: true,
    ignoreHTTPSErrors: true,
  },
  // 프로젝트 max-width: 480px → Galaxy S25(430px)와 iPhone 12(390px) 두 사이즈 검증
  projects: [
    {
      name: 'Galaxy S25',
      use: { ...devices['Galaxy S25'] },   // 430 x 932 (Chromium)
    },
    {
      name: 'iPhone 12',
      // WebKit 미설치 환경 대비 — Chromium으로 동일 뷰포트 에뮬레이션
      use: {
        ...devices['Galaxy S23'],          // 360 x 780 Chromium 기반
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 3,
      },
    },
  ],
  // webServer 없음 — 배포된 사이트를 직접 타겟
});
