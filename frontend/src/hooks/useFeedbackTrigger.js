/**
 * useFeedbackTrigger - (비활성화) 장 시간 체크 유틸 제공
 * 기존 60초 자동 팝업 → 전용 설문 페이지로 대체
 */

/**
 * 현재 장 시간(09:00~15:30 KST) 여부 확인
 */
export function isMarketHours() {
  const now = new Date();
  const kstHour = (now.getUTCHours() + 9) % 24;
  const kstMin = now.getUTCMinutes();
  const kstTime = kstHour * 100 + kstMin;
  return kstTime >= 900 && kstTime <= 1530;
}

export default function useFeedbackTrigger() {
  // 자동 팝업 비활성화 — 전용 설문 페이지(/feedback-survey)로 대체
  return { showFeedback: false, closeFeedback: () => {} };
}
