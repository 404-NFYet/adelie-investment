import { useCallback } from 'react';
import { TutorUIProvider, useTutorUI } from './TutorUIContext';
import { TutorSessionProvider, useTutorSession } from './TutorSessionContext';
import { TutorChatProvider, useTutorChat } from './TutorChatContext';

export function TutorProvider({ children }) {
  return (
    <TutorUIProvider>
      <TutorSessionProvider>
        <TutorChatProvider>
          {children}
        </TutorChatProvider>
      </TutorSessionProvider>
    </TutorUIProvider>
  );
}

/**
 * useTutor — 하위 호환 wrapper.
 * 기존 컴포넌트에서 useTutor()를 그대로 사용할 수 있도록 3개 context를 합쳐 반환.
 * 고성능이 필요한 경우 useTutorChat()/useTutorSession()/useTutorUI() 각각 사용.
 */
export function useTutor() {
  const ui = useTutorUI();
  const session = useTutorSession();
  const chat = useTutorChat();

  const {
    openTutor: openTutorUI,
    closeTutor,
    contextInfo,
    setContextInfo,
    currentTerm,
    setCurrentTerm,
    agentStatus,
    setAgentStatus,
    requestVisualization: requestVisualizationUI,
    DEFAULT_AGENT_STATUS,
  } = ui;
  const {
    sessions,
    activeSessionId,
    refreshSessions,
    createNewChat: createNewChatSession,
    deleteChat: deleteChatSession,
    setActiveSessionId,
  } = session;
  const {
    messages,
    assistantTurns,
    isLoading,
    sendMessage: sendChatMessage,
    clearMessages: clearChatMessages,
    loadChatHistory: loadChatHistoryRaw,
    setSessionId,
  } = chat;

  const openTutor = useCallback((termOrContext = null) => {
    openTutorUI(termOrContext, refreshSessions);
  }, [openTutorUI, refreshSessions]);

  const createNewChat = useCallback(async () => {
    return createNewChatSession((nextSessionId) => {
      clearChatMessages();
      setCurrentTerm(null);
      setAgentStatus(DEFAULT_AGENT_STATUS);
      setSessionId(nextSessionId);
      setActiveSessionId(nextSessionId);
    });
  }, [createNewChatSession, clearChatMessages, setCurrentTerm, setAgentStatus, DEFAULT_AGENT_STATUS, setSessionId, setActiveSessionId]);

  const deleteChat = useCallback(async (id) => {
    return deleteChatSession(id, () => {
      clearChatMessages();
      setSessionId(null);
      setCurrentTerm(null);
      setAgentStatus(DEFAULT_AGENT_STATUS);
    });
  }, [deleteChatSession, clearChatMessages, setSessionId, setCurrentTerm, setAgentStatus, DEFAULT_AGENT_STATUS]);

  const loadChatHistory = useCallback(async (id) => {
    return loadChatHistoryRaw(id, setActiveSessionId);
  }, [loadChatHistoryRaw, setActiveSessionId]);

  const sendMessage = useCallback(async (message, difficulty = 'beginner', options = {}) => {
    await sendChatMessage(
      message,
      difficulty,
      contextInfo,
      setAgentStatus,
      (newSessionId) => {
        setActiveSessionId(newSessionId);
      },
      options,
    );
    await refreshSessions();
  }, [sendChatMessage, contextInfo, setAgentStatus, setActiveSessionId, refreshSessions]);

  const requestVisualization = useCallback((query) => {
    requestVisualizationUI(query, (msg, diff) => sendMessage(msg, diff));
  }, [requestVisualizationUI, sendMessage]);

  const clearMessages = useCallback(() => {
    clearChatMessages();
    setCurrentTerm(null);
    setActiveSessionId(null);
    setAgentStatus(DEFAULT_AGENT_STATUS);
  }, [clearChatMessages, setCurrentTerm, setActiveSessionId, setAgentStatus, DEFAULT_AGENT_STATUS]);

  return {
    // UI
    isOpen: ui.isOpen,
    openTutor,
    closeTutor,
    contextInfo,
    setContextInfo,
    currentTerm,
    setCurrentTerm,
    agentStatus,
    requestVisualization,
    // Session
    sessions,
    activeSessionId,
    refreshSessions,
    createNewChat,
    deleteChat,
    // Chat
    messages,
    assistantTurns,
    isLoading,
    sendMessage,
    clearMessages,
    loadChatHistory,
  };
}
