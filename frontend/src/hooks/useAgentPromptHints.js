import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';

const HIDDEN_PREFIXES = ['/auth', '/landing', '/onboarding', '/tutor'];
const HIDDEN_EXACT = ['/'];

export default function useAgentPromptHints() {
  const location = useLocation();

  return useMemo(() => {
    const { pathname, state } = location;

    const shouldHide =
      HIDDEN_EXACT.includes(pathname) ||
      HIDDEN_PREFIXES.some((prefix) => pathname.startsWith(prefix));

    let mode = 'home';
    if (pathname.startsWith('/portfolio')) mode = 'stock';
    if (pathname.startsWith('/profile')) mode = 'my';
    if (pathname.startsWith('/agent')) mode = state?.mode || 'home';

    const configByMode = {
      home: {
        placeholder: '오늘 브리핑에서 궁금한 점이 있나요?',
        suggestedPrompt: '외국인 매도 이슈가 내 투자에 어떤 영향이 있어?',
      },
      stock: {
        placeholder: '종목명이나 궁금한 점을 입력하세요',
        suggestedPrompt: '이 종목 지금 흐름을 기준으로 체크포인트 정리해줘',
      },
      my: {
        placeholder: '오늘 학습한 내용을 복습해볼까요?',
        suggestedPrompt: '내가 최근 배운 개념 3개를 정리해줘',
      },
    };

    const modeConfig = configByMode[mode] || configByMode.home;

    return {
      shouldHide,
      mode,
      placeholder: modeConfig.placeholder,
      suggestedPrompt: modeConfig.suggestedPrompt,
    };
  }, [location]);
}
