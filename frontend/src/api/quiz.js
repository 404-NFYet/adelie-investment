import { API_BASE_URL, postJson } from './client';

export const quizApi = {
  claimReward: (payload) =>
    postJson(`${API_BASE_URL}/api/v1/quiz/reward`, payload),
};
