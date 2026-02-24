import { useCallback } from 'react';
import { AgentUIProvider, useAgentUI } from './AgentUIContext';
import { AgentSessionProvider, useAgentSession } from './AgentSessionContext';
import { AgentChatProvider, useAgentChat } from './AgentChatContext';

export function AgentProvider({ children }) {
  return (
    <AgentUIProvider>
      <AgentSessionProvider>
        <AgentChatProvider>
          {children}
        </AgentChatProvider>
      </AgentSessionProvider>
    </AgentUIProvider>
  );
}

/**
 * useAgent — 3개 Agent context를 합쳐 반환하는 합성 훅.
 * 고성능이 필요한 경우 useAgentChat()/useAgentSession()/useAgentUI() 각각 사용.
 */
export function useAgent() {
  const ui = useAgentUI();
  const session = useAgentSession();
  const chat = useAgentChat();

  const {
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
    isStreamingActive,
    canRegenerate,
    sessionId,
    sendMessage: sendChatMessage,
    stopGeneration: stopGenerationRaw,
    regenerateLastResponse: regenerateLastResponseRaw,
    clearMessages: clearChatMessages,
    loadChatHistory: loadChatHistoryRaw,
    setSessionId,
  } = chat;

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
    const contextInfoToUse = options?.contextInfoOverride || contextInfo;
    const chatOptions = options?.chatOptions || options;
    await sendChatMessage(
      message,
      difficulty,
      contextInfoToUse,
      setAgentStatus,
      (newSessionId) => {
        setActiveSessionId(newSessionId);
      },
      chatOptions,
    );
    await refreshSessions();
  }, [sendChatMessage, contextInfo, setAgentStatus, setActiveSessionId, refreshSessions]);

  const stopGeneration = useCallback(() => {
    return stopGenerationRaw();
  }, [stopGenerationRaw]);

  const regenerateLastResponse = useCallback(async (options = {}) => {
    const success = await regenerateLastResponseRaw(
      setAgentStatus,
      (newSessionId) => {
        setActiveSessionId(newSessionId);
      },
      {
        difficulty: options?.difficulty,
        contextInfo: options?.contextInfoOverride || contextInfo,
        options: options?.chatOptions,
      },
    );

    if (success) {
      await refreshSessions();
    }

    return success;
  }, [regenerateLastResponseRaw, setAgentStatus, setActiveSessionId, contextInfo, refreshSessions]);

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
    isStreamingActive,
    canRegenerate,
    sessionId,
    sendMessage,
    stopGeneration,
    regenerateLastResponse,
    clearMessages,
    loadChatHistory,
  };
}

// 하위 호환 alias
export const useTutor = useAgent;
