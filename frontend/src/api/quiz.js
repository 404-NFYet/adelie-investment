/**
 * quiz.js - 퀴즈 보상 API
 */
import { postJson } from './client';

export const submitQuizReward = (scenarioId, selectedAnswer, correctAnswer) =>
  postJson('/api/v1/quiz/reward', {
    scenario_id: scenarioId,
    selected_answer: selectedAnswer,
    correct_answer: correctAnswer,
  });
