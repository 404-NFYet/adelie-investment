/**
 * 피드백 API 모듈
 */
import { API_BASE_URL, postJson } from './client';

export const feedbackApi = {
  /** 인앱 피드백 제출 */
  submit: (data) => postJson(`${API_BASE_URL}/api/v1/feedback`, data),

  /** 브리핑 완독 피드백 */
  submitBriefing: (data) => postJson(`${API_BASE_URL}/api/v1/feedback/briefing`, data),

  /** 콘텐츠 반응 (좋아요/싫어요) */
  submitReaction: (data) => postJson(`${API_BASE_URL}/api/v1/feedback/reaction`, data),

  /** 피드백 설문 제출 */
  submitSurvey: (data) => postJson(`${API_BASE_URL}/api/v1/feedback/survey`, data),

  /** 에러 스크린샷 업로드 (multipart/form-data) */
  uploadScreenshot: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_BASE_URL}/api/v1/feedback/screenshot`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) throw new Error('스크린샷 업로드 실패');
    return response.json();
  },
};
