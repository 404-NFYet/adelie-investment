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

  const openTutor = useCallback((termOrContext = null) => {
    ui.openTutor(termOrContext, session.refreshSessions);
  }, [ui, session.refreshSessions]);

  const createNewChat = useCallback(async () => {
    return session.createNewChat((nextSessionId) => {
      chat.clearMessages();
      ui.setCurrentTerm(null);
      ui.setAgentStatus(ui.DEFAULT_AGENT_STATUS);
      chat.setSessionId(nextSessionId);
      session.setActiveSessionId(nextSessionId);
    });
  }, [session, chat, ui]);

  const deleteChat = useCallback(async (id) => {
    return session.deleteChat(id, () => {
      chat.clearMessages();
      chat.setSessionId(null);
      ui.setCurrentTerm(null);
      ui.setAgentStatus(ui.DEFAULT_AGENT_STATUS);
    });
  }, [session, chat, ui]);

  const loadChatHistory = useCallback(async (id) => {
    return chat.loadChatHistory(id, session.setActiveSessionId);
  }, [chat, session]);

  const sendMessage = useCallback(async (message, difficulty = 'beginner') => {
    await chat.sendMessage(
      message,
      difficulty,
      ui.contextInfo,
      ui.setAgentStatus,
      (newSessionId) => {
        session.setActiveSessionId(newSessionId);
      },
    );
    await session.refreshSessions();
  }, [chat, ui, session]);

  const requestVisualization = useCallback((query) => {
    ui.requestVisualization(query, (msg, diff) => sendMessage(msg, diff));
  }, [ui, sendMessage]);

  const clearMessages = useCallback(() => {
    chat.clearMessages();
    ui.setCurrentTerm(null);
    session.setActiveSessionId(null);
    ui.setAgentStatus(ui.DEFAULT_AGENT_STATUS);
  }, [chat, ui, session]);

  return {
    // UI
    isOpen: ui.isOpen,
    openTutor,
    closeTutor: ui.closeTutor,
    contextInfo: ui.contextInfo,
    setContextInfo: ui.setContextInfo,
    currentTerm: ui.currentTerm,
    setCurrentTerm: ui.setCurrentTerm,
    agentStatus: ui.agentStatus,
    requestVisualization,
    // Session
    sessions: session.sessions,
    activeSessionId: session.activeSessionId,
    refreshSessions: session.refreshSessions,
    createNewChat,
    deleteChat,
    // Chat
    messages: chat.messages,
    isLoading: chat.isLoading,
    sendMessage,
    clearMessages,
    loadChatHistory,
  };
}
