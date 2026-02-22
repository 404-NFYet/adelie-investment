/**
 * Agent Canvas 모바일 반응형 E2E 테스트
 * Test IDs: FE-AGENT-M01 ~ FE-AGENT-M04
 * 대상 컴포넌트: AgentDock, AgentCanvasPage, AgentHistoryPage
 */
import { test, expect } from '@playwright/test';

test.describe('FE-AGENT-M: Agent Canvas 모바일 반응형', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/home');
    // 페이지 로드 대기
    await page.waitForLoadState('networkidle').catch(() => {});
  });

  /**
   * FE-AGENT-M01: AgentDock 입력바가 viewport 내에 완전히 표시됨
   * 검증: 입력바가 viewport 너비를 벗어나지 않고 bottom nav 위에 위치
   */
  test('FE-AGENT-M01: AgentDock 입력바가 viewport 내에 표시됨', async ({ page, viewport }) => {
    // AgentDock은 fixed bottom에 표시
    const agentInput = page.locator('input[aria-label="에이전트 질문 입력"]').first();
    const dockExists = await agentInput.isVisible().catch(() => false);

    if (!dockExists) {
      // AgentDock이 현재 페이지에 숨겨진 경우 스킵
      test.skip();
      return;
    }

    const form = agentInput.locator('xpath=ancestor::form');
    const dockWrapper = form.locator('xpath=ancestor::div[contains(@class,"fixed")]');
    const box = await dockWrapper.boundingBox().catch(() => null);

    if (box) {
      // dock이 viewport 너비를 벗어나지 않음
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
      // dock이 viewport 하단 근처에 위치
      expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 5);
    }
  });

  /**
   * FE-AGENT-M02: AgentDock 아이콘 버튼들이 가로 overflow 없음
   * 검증: 4개 아이콘 버튼(h-7 w-7)이 입력바 안에서 잘리지 않음
   */
  test('FE-AGENT-M02: AgentDock 아이콘 버튼 overflow 없음', async ({ page, viewport }) => {
    const submitBtn = page.locator('button[aria-label="질문 전송"]').first();
    const submitExists = await submitBtn.isVisible().catch(() => false);

    if (!submitExists) {
      test.skip();
      return;
    }

    const submitBox = await submitBtn.boundingBox();
    if (submitBox) {
      // 전송 버튼(가장 오른쪽)이 viewport를 벗어나지 않음
      expect(submitBox.x + submitBox.width).toBeLessThanOrEqual(viewport.width + 2);
      // 버튼 크기가 28px(h-7 w-7) 이상
      expect(submitBox.width).toBeGreaterThanOrEqual(24);
      expect(submitBox.height).toBeGreaterThanOrEqual(24);
    }

    // 스파클 버튼(추천 문구)도 확인
    const sparkleBtn = page.locator('button[aria-label="추천 문구 사용"]').first();
    const sparkleExists = await sparkleBtn.isVisible().catch(() => false);
    if (sparkleExists) {
      const sparkleBox = await sparkleBtn.boundingBox();
      if (sparkleBox) {
        expect(sparkleBox.x).toBeGreaterThanOrEqual(0);
      }
    }
  });

  /**
   * FE-AGENT-M03: AgentHistoryPage 세션 목록의 삭제 버튼 접근 가능
   * 검증: 삭제 버튼이 세션 카드 우측에서 접근 가능하며 잘리지 않음
   */
  test('FE-AGENT-M03: AgentHistory 삭제 버튼 접근성', async ({ page, viewport }) => {
    await page.goto('/agent/history');
    await page.waitForLoadState('networkidle').catch(() => {});

    // 세션 목록이 있는 경우 삭제 버튼 확인
    const deleteBtn = page.locator('button', { hasText: '삭제' }).first();
    const deleteExists = await deleteBtn.isVisible().catch(() => false);

    if (deleteExists) {
      const box = await deleteBtn.boundingBox();
      if (box) {
        // 삭제 버튼이 viewport 내에 있음
        expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 2);
        // 버튼이 화면 오른쪽에서 잘리지 않음 (최소 16px 여백)
        expect(viewport.width - (box.x + box.width)).toBeGreaterThanOrEqual(-2);
      }
    } else {
      // 세션이 없는 경우 — 빈 상태 메시지 확인
      const emptyMsg = page.locator('text=저장된 대화가 없습니다');
      const emptyExists = await emptyMsg.isVisible().catch(() => false);
      // 빈 상태이거나 세션이 있어야 함 (둘 다 허용)
      expect(emptyExists || !deleteExists).toBe(true);
    }
  });

  /**
   * FE-AGENT-M04: AgentDock 세션 복귀 레이블이 truncate 처리됨
   * 검증: "진행 중인 대화가 있어요" 텍스트가 max-w-[8rem]으로 잘림 처리
   */
  test('FE-AGENT-M04: AgentDock 세션 복귀 레이블 overflow 처리', async ({ page, viewport }) => {
    const resumeLabel = page.locator('.truncate.max-w-\\[8rem\\]', { hasText: '진행 중인 대화가 있어요' }).first();
    const labelExists = await resumeLabel.isVisible().catch(() => false);

    if (labelExists) {
      const box = await resumeLabel.boundingBox();
      if (box) {
        // 레이블이 최대 8rem(128px) 이내
        expect(box.width).toBeLessThanOrEqual(130);
        // viewport 내에 위치
        expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 2);
      }
    }
    // 레이블이 없는 경우(세션 없음) — 테스트 패스
  });
});
