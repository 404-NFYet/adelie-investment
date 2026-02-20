/**
 * TutorChat.jsx - AI 튜터 진입점
 * /tutor 직접 접근 시 TutorModal을 자동으로 오픈
 */
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTutor } from '../contexts';

export default function TutorChat() {
  const { openTutor, isOpen } = useTutor();
  const navigate = useNavigate();
  const hasEverBeenOpen = useRef(false);

  // 마운트 시 모달 자동 오픈
  useEffect(() => {
    openTutor();
  }, [openTutor]);

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
