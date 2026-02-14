/**
 * TermContext.jsx - 용어 바텀시트 상태 관리
 * 하이라이트된 용어 클릭 시 바텀시트를 열고, 필요 시 AI 튜터로 연결
 */
import { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { useTutor } from './TutorContext';

const TermContext = createContext(null);

export function TermProvider({ children }) {
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [isTermSheetOpen, setIsTermSheetOpen] = useState(false);
  const { openTutor } = useTutor();

  // 바텀시트 열기
  const openTermSheet = useCallback((term) => {
    setSelectedTerm(term);
    setIsTermSheetOpen(true);
  }, []);

  // 바텀시트 닫기
  const closeTermSheet = useCallback(() => {
    setIsTermSheetOpen(false);
    setSelectedTerm(null);
  }, []);

  // 바텀시트 닫고 AI 튜터 채팅으로 이동
  const openTutorWithTerm = useCallback((term) => {
    setIsTermSheetOpen(false);
    setSelectedTerm(null);
    openTutor(term);
  }, [openTutor]);

  const value = useMemo(() => ({
    selectedTerm,
    isTermSheetOpen,
    openTermSheet,
    closeTermSheet,
    openTutorWithTerm,
  }), [selectedTerm, isTermSheetOpen, openTermSheet, closeTermSheet, openTutorWithTerm]);

  return (
    <TermContext.Provider value={value}>
      {children}
    </TermContext.Provider>
  );
}

export function useTermContext() {
  const context = useContext(TermContext);
  if (!context) throw new Error('useTermContext must be used within a TermProvider');
  return context;
}
