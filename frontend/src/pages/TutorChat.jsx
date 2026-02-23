/**
 * TutorChat.jsx - AI 튜터 진입점
 * /tutor 직접 접근 시 TutorModal을 자동으로 오픈
 * location.state를 통해 initialPrompt, stockContext, mode 수신 가능
 */
import { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTutor } from '../contexts';

export default function TutorChat() {
  const { openTutor, isOpen, sendMessage, setContextInfo, clearMessages } = useTutor();
  const navigate = useNavigate();
  const location = useLocation();
  const hasEverBeenOpen = useRef(false);
  const initialPromptSent = useRef(false);

  // 마운트 시 모달 자동 오픈
  useEffect(() => {
    const state = location.state;

    // resetConversation 요청 시 대화 초기화
    if (state?.resetConversation) {
      clearMessages?.();
    }

    // stockContext 또는 contextPayload가 있으면 contextInfo 설정
    const ctx = state?.stockContext || state?.contextPayload;
    if (ctx) {
      setContextInfo?.(ctx);
    }

    openTutor();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 모달이 열린 후 initialPrompt 자동 전송 (최초 1회)
  useEffect(() => {
    const state = location.state;
    if (isOpen && state?.initialPrompt && !initialPromptSent.current) {
      initialPromptSent.current = true;
      // 모달 렌더링 안정화 후 메시지 전송
      setTimeout(() => {
        sendMessage?.(state.initialPrompt, 'beginner');
      }, 300);
    }
  }, [isOpen, location.state, sendMessage]);

  // isOpen이 실제로 true가 된 이후에만 닫힘 감지 → 홈 이동
  useEffect(() => {
    if (isOpen) {
      hasEverBeenOpen.current = true;
    } else if (hasEverBeenOpen.current) {
      navigate('/home', { replace: true });
    }
  }, [isOpen, navigate]);

  // 빈 배경 — TutorModal이 오버레이로 표시됨
  return <div className="min-h-screen bg-background" />;
}
