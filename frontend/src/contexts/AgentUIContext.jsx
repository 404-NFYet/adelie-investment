import { createContext, useContext, useState, useCallback } from 'react';

const AgentUIContext = createContext(null);

const DEFAULT_AGENT_STATUS = {
  phase: 'idle',
  text: '응답 대기 중',
};

export function AgentUIProvider({ children }) {
  const [contextInfo, setContextInfo] = useState(null);
  const [currentTerm, setCurrentTerm] = useState(null);
  const [agentStatus, setAgentStatus] = useState(DEFAULT_AGENT_STATUS);

  const requestVisualization = useCallback((query, sendMessage) => {
    sendMessage(`${query} (차트로 보여주세요)`, 'beginner');
  }, []);

  return (
    <AgentUIContext.Provider value={{
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
    </AgentUIContext.Provider>
  );
}

export function useAgentUI() {
  const ctx = useContext(AgentUIContext);
  if (!ctx) throw new Error('useAgentUI must be used within AgentUIProvider');
  return ctx;
}
