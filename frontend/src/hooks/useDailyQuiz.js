import { useCallback, useEffect, useMemo, useState } from 'react';
import { quizApi } from '../api/quiz';
import { getKstTodayDateKey } from '../utils/kstDate';

const STORAGE_KEY = 'adelie_daily_quiz_v1';

const FALLBACK_KEYWORDS = [
  {
    title: '리스크 관리',
    description: '큰 손실을 막기 위해 분산 투자하는 전략',
  },
  {
    title: '수급 변화',
    description: '외국인과 기관의 매매 흐름을 파악하는 것',
  },
  {
    title: '실적 모멘텀',
    description: '기업의 이익이 늘어날 것이라는 기대감',
  },
  {
    title: '거시 변수',
    description: '금리나 환율 등 시장 전체에 영향을 주는 지표',
  },
];

function createEmptyState(dateKey) {
  return {
    dateKey,
    rewardAttempted: false,
    paidQuestionIds: [],
    lastScore: 0,
    lastRewardTotal: 0,
    lastAttemptAt: null,
  };
}

function readRawState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function readDailyState(dateKey) {
  const parsed = readRawState();
  if (!parsed || parsed.dateKey !== dateKey) return createEmptyState(dateKey);

  return {
    dateKey,
    rewardAttempted: Boolean(parsed.rewardAttempted),
    paidQuestionIds: Array.isArray(parsed.paidQuestionIds) ? parsed.paidQuestionIds : [],
    lastScore: Number(parsed.lastScore || 0),
    lastRewardTotal: Number(parsed.lastRewardTotal || 0),
    lastAttemptAt: parsed.lastAttemptAt || null,
  };
}

function writeDailyState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore localStorage errors
  }
}

function normalizeKeywords(keywords) {
  const items = Array.isArray(keywords) ? keywords : [];
  const normalized = items
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      title: String(item.title || '').trim(),
      description: String(item.description || '').trim(),
    }))
    .filter((item) => item.title.length > 0);

  const deduped = [];
  const seen = new Set();
  for (const item of normalized) {
    const key = item.title.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(item);
  }

  return deduped;
}

function takeQuestionSeeds(keywords) {
  const keywordPool = normalizeKeywords(keywords);
  const merged = [...keywordPool, ...FALLBACK_KEYWORDS];
  const seeds = [];

  for (const item of merged) {
    if (seeds.length >= 3) break;
    seeds.push(item);
  }

  while (seeds.length < 3) {
    seeds.push(FALLBACK_KEYWORDS[seeds.length % FALLBACK_KEYWORDS.length]);
  }

  return { keywordPool: merged, seeds };
}

function shortenText(text) {
  if (!text) return '';
  const firstSentence = text.split(/[.?!](\s|$)/)[0].trim();
  if (firstSentence.length > 35) {
    return firstSentence.substring(0, 32) + '...';
  }
  return firstSentence;
}

function buildOptions(correctDescription, wrongPool, idx) {
  const wrongs = [];
  for (const candidate of wrongPool) {
    const text = shortenText(candidate);
    if (!text || text === correctDescription || wrongs.includes(text)) continue;
    wrongs.push(text);
    if (wrongs.length >= 3) break;
  }

  const fallbackWrongs = [
    '장기적인 가격 추세를 따라가는 전략',
    '거래량 급증과 뉴스 강도만 분석하는 것',
    '평균 단가를 낮추기 위해 계속 매수하는 것',
    '오로지 차트의 기술적 지표만 보고 판단하는 것'
  ];

  for (const fallback of fallbackWrongs) {
    if (wrongs.length >= 3) break;
    if (fallback !== correctDescription && !wrongs.includes(fallback)) {
      wrongs.push(fallback);
    }
  }

  const base = [correctDescription, ...wrongs.slice(0, 3)];
  const rotate = idx % base.length;
  const options = [...base.slice(rotate), ...base.slice(0, rotate)];
  const correctAnswer = options.findIndex((option) => option === correctDescription);

  return { options, correctAnswer };
}

function buildDailyQuestions(keywords, dateKey) {
  const { keywordPool, seeds } = takeQuestionSeeds(keywords);
  const fallbackDescriptions = keywordPool.map((item) => item.description).filter(Boolean);

  return seeds.map((seed, idx) => {
    const rawDesc = seed.description || `${seed.title} 관련 변화를 점검하는 것`;
    const correctDescription = shortenText(rawDesc);
    const wrongPool = fallbackDescriptions.filter((desc) => desc !== rawDesc);
    const { options, correctAnswer } = buildOptions(correctDescription, wrongPool, idx);

    return {
      id: `q-${idx + 1}`,
      scenarioId: `daily-${dateKey}-${idx + 1}`,
      title: seed.title,
      prompt: `다음 중 "${seed.title}"에 대한 가장 적절한 설명은?`,
      options,
      correctAnswer,
    };
  });
}

function evaluateAnswers(questions, answers) {
  const answerMap = answers || {};
  let score = 0;

  for (const question of questions) {
    if (answerMap[question.id] === question.correctAnswer) {
      score += 1;
    }
  }

  return {
    score,
    total: questions.length,
  };
}

export default function useDailyQuiz(keywords) {
  const dateKey = getKstTodayDateKey();
  const questions = useMemo(() => buildDailyQuestions(keywords, dateKey), [keywords, dateKey]);
  const [dailyState, setDailyState] = useState(() => readDailyState(dateKey));

  useEffect(() => {
    setDailyState(readDailyState(dateKey));
  }, [dateKey]);

  const persistState = useCallback((nextState) => {
    writeDailyState(nextState);
    setDailyState(nextState);
  }, []);

  const settleReward = useCallback(async (answers, onlyUnpaid = false) => {
    const current = readDailyState(dateKey);
    const paidSet = new Set(current.paidQuestionIds || []);
    const targets = questions.filter((question) => !paidSet.has(question.id));
    const evaluation = evaluateAnswers(questions, answers);

    if (onlyUnpaid && targets.length === 0) {
      return {
        mode: 'reward',
        ...evaluation,
        rewardTotal: 0,
        failedQuestionIds: [],
        paidQuestionIds: current.paidQuestionIds,
        remainingRewardQuestions: 0,
      };
    }

    let rewardTotal = 0;
    const failedQuestionIds = [];
    const errorMessages = [];

    for (const question of targets) {
      const selectedAnswer = Number.isInteger(answers?.[question.id]) ? answers[question.id] : -1;

      try {
        const response = await quizApi.claimReward({
          scenario_id: question.scenarioId,
          selected_answer: selectedAnswer,
          correct_answer: question.correctAnswer,
        });

        rewardTotal += Number(response?.reward_amount || 0);
        paidSet.add(question.id);
      } catch (error) {
        failedQuestionIds.push(question.id);
        errorMessages.push(error?.message || `${question.id} 보상 지급에 실패했습니다.`);
      }
    }

    const nextState = {
      dateKey,
      rewardAttempted: true,
      paidQuestionIds: Array.from(paidSet),
      lastScore: evaluation.score,
      lastRewardTotal: rewardTotal,
      lastAttemptAt: new Date().toISOString(),
    };

    persistState(nextState);

    return {
      mode: 'reward',
      ...evaluation,
      rewardTotal,
      failedQuestionIds,
      errorMessages,
      paidQuestionIds: nextState.paidQuestionIds,
      remainingRewardQuestions: questions.length - nextState.paidQuestionIds.length,
    };
  }, [dateKey, persistState, questions]);

  const submitQuiz = useCallback(async (answers) => {
    const current = readDailyState(dateKey);
    const evaluation = evaluateAnswers(questions, answers);

    if (current.rewardAttempted) {
      const nextState = {
        ...current,
        lastScore: evaluation.score,
        lastRewardTotal: 0,
        lastAttemptAt: new Date().toISOString(),
      };
      persistState(nextState);

      return {
        mode: 'practice',
        ...evaluation,
        rewardTotal: 0,
        failedQuestionIds: [],
        paidQuestionIds: nextState.paidQuestionIds,
        remainingRewardQuestions: questions.length - nextState.paidQuestionIds.length,
      };
    }

    return settleReward(answers, false);
  }, [dateKey, persistState, questions, settleReward]);

  const retryUnpaidRewards = useCallback(async (answers) => {
    const current = readDailyState(dateKey);
    if (!current.rewardAttempted) {
      return submitQuiz(answers);
    }

    if ((current.paidQuestionIds || []).length >= questions.length) {
      return {
        mode: 'reward',
        ...evaluateAnswers(questions, answers),
        rewardTotal: 0,
        failedQuestionIds: [],
        paidQuestionIds: current.paidQuestionIds,
        remainingRewardQuestions: 0,
      };
    }

    return settleReward(answers, true);
  }, [dateKey, questions, settleReward, submitQuiz]);

  const paidCount = dailyState.paidQuestionIds.length;
  const totalQuestions = questions.length;
  const hasPendingRewards = dailyState.rewardAttempted && paidCount < totalQuestions;
  const hasClaimedAllRewards = dailyState.rewardAttempted && paidCount >= totalQuestions;

  return {
    dateKey,
    questions,
    dailyState,
    paidCount,
    totalQuestions,
    hasPendingRewards,
    hasClaimedAllRewards,
    submitQuiz,
    retryUnpaidRewards,
  };
}
