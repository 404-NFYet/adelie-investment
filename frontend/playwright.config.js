import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'line',
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
    },
    // ── 모바일 기기 9종 ──
    {
      name: 'iPhone SE 3rd',
      use: { ...devices['iPhone SE'] },
    },
    {
      name: 'iPhone 16',
      use: {
        ...devices['iPhone 15'],
        viewport: { width: 393, height: 852 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'iPhone 16 Plus',
      use: {
        ...devices['iPhone 15 Plus'],
        viewport: { width: 430, height: 932 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'iPhone 16 Pro',
      use: {
        ...devices['iPhone 15 Pro'],
        viewport: { width: 402, height: 874 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'iPhone 16 Pro Max',
      use: {
        ...devices['iPhone 15 Pro Max'],
        viewport: { width: 440, height: 956 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'Galaxy S24',
      use: { ...devices['Galaxy S24'] },
    },
    {
      name: 'Galaxy S25',
      use: {
        ...devices['Galaxy S24'],
        viewport: { width: 360, height: 780 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'Galaxy S25 Plus',
      use: {
        ...devices['Galaxy S24'],
        viewport: { width: 412, height: 891 },
        deviceScaleFactor: 3,
      },
    },
    {
      name: 'Galaxy S25 Ultra',
      use: {
        ...devices['Galaxy S24'],
        viewport: { width: 412, height: 891 },
        deviceScaleFactor: 3.5,
      },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3001',
    reuseExistingServer: true,
  },
});
