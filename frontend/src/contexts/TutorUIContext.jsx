import { createContext, useContext, useState, useCallback } from 'react';

const TutorUIContext = createContext(null);

const DEFAULT_AGENT_STATUS = {
  phase: 'idle',
  text: '응답 대기 중',
};

export function TutorUIProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [contextInfo, setContextInfo] = useState(null);
  const [currentTerm, setCurrentTerm] = useState(null);
  const [agentStatus, setAgentStatus] = useState(DEFAULT_AGENT_STATUS);

  const openTutor = useCallback((termOrContext = null, onOpen = null) => {
    setIsOpen(true);
    if (typeof termOrContext === 'string') {
      setCurrentTerm(termOrContext);
    } else if (termOrContext) {
      setContextInfo(termOrContext);
    }
    if (onOpen) onOpen();
  }, []);

  const closeTutor = useCallback(() => {
    setIsOpen(false);
    setCurrentTerm(null);
    setAgentStatus(DEFAULT_AGENT_STATUS);
  }, []);

  const requestVisualization = useCallback((query, sendMessage) => {
    sendMessage(`${query} (차트로 보여주세요)`, 'beginner');
  }, []);

  return (
    <TutorUIContext.Provider value={{
      isOpen,
      openTutor,
      closeTutor,
      contextInfo,
      setContextInfo,
      currentTerm,
      setCurrentTerm,
      agentStatus,
      setAgentStatus,
      requestVisualization,
      DEFAULT_AGENT_STATUS,
    }}>
      {children}
    </TutorUIContext.Provider>
  );
}

export function useTutorUI() {
  const ctx = useContext(TutorUIContext);
  if (!ctx) throw new Error('useTutorUI must be used within TutorUIProvider');
  return ctx;
}
