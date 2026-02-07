// @ts-check
import { test, expect } from '@playwright/test';

test.describe('백엔드 API 응답 검증', () => {
  test('health 엔드포인트', async ({ request }) => {
    const res = await request.get('/api/v1/health');
    expect(res.status()).toBe(200);
    expect((await res.json()).status).toBe('healthy');
  });

  test('keywords/today 엔드포인트 (fallback 포함)', async ({ request }) => {
    const res = await request.get('/api/v1/keywords/today');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.keywords).toBeDefined();
    expect(data.keywords.length).toBeGreaterThan(0);
  });

  test('narrative/6 엔드포인트', async ({ request }) => {
    const res = await request.get('/api/v1/narrative/6');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.steps).toBeDefined();
    expect(Object.keys(data.steps).length).toBe(6);
  });

  test('tutor/sessions 엔드포인트', async ({ request }) => {
    const res = await request.get('/api/v1/tutor/sessions');
    expect(res.status()).toBe(200);
    expect(Array.isArray(await res.json())).toBe(true);
  });

  test('tutor/explain/PER 엔드포인트', async ({ request }) => {
    const res = await request.get('/api/v1/tutor/explain/PER');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.term).toBe('PER');
    expect(data.explanation).toBeDefined();
  });

  test('keywords/popular 엔드포인트', async ({ request }) => {
    const res = await request.get('/api/v1/keywords/popular');
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data.keywords).toBeDefined();
  });
});
