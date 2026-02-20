import { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { API_BASE_URL, authFetch, fetchJson, postJson, deleteJson } from '../api/client';

const TutorContext = createContext(null);
const SESSION_KEY = 'adelie_tutor_session';

const DEFAULT_AGENT_STATUS = {
  phase: 'idle',
  text: '응답 대기 중',
};

const parseVisualizationPayload = (content) => {
  if (!content) return null;
  if (typeof content === 'object') return content;
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
};

const mapHistoryMessage = (message, index) => {
  if (message.message_type === 'visualization') {
    const parsed = parseVisualizationPayload(message.content);
    return {
      id: `${message.id || Date.now()}-viz-${index}`,
      role: 'visualization',
      content: parsed?.html || parsed?.content || message.chart_url || message.content || null,
      format: parsed?.chartData ? 'json' : (parsed?.format || 'html'),
      chartData: parsed?.chartData || null,
      executionTime: message.execution_time_ms || parsed?.execution_time_ms,
      timestamp: message.created_at,
      isStreaming: false,
    };
  }

  return {
    id: `${message.id || Date.now()}-${index}`,
    role: message.role,
    content: message.content,
    timestamp: message.created_at,
    isStreaming: false,
  };
};

export function TutorProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    try {
      return localStorage.getItem(SESSION_KEY) || null;
    } catch {
      return null;
    }
  });
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [contextInfo, setContextInfo] = useState(null);
  const [currentTerm, setCurrentTerm] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      return localStorage.getItem(SESSION_KEY) || null;
    } catch {
      return null;
    }
  });
  const [agentStatus, setAgentStatus] = useState(DEFAULT_AGENT_STATUS);

  useEffect(() => {
    try {
      if (sessionId) localStorage.setItem(SESSION_KEY, sessionId);
      else localStorage.removeItem(SESSION_KEY);
    } catch {
      // ignore localStorage errors
    }
  }, [sessionId]);

  const refreshSessions = useCallback(async () => {
    try {
      const sessionList = await fetchJson(`${API_BASE_URL}/api/v1/tutor/sessions`);
      setSessions(Array.isArray(sessionList) ? sessionList : []);
    } catch (error) {
      console.error('세션 목록 조회 실패:', error);
      setSessions([]);
    }
  }, []);

  const openTutor = useCallback((termOrContext = null) => {
    setIsOpen(true);
    if (typeof termOrContext === 'string') {
      setCurrentTerm(termOrContext);
    } else if (termOrContext) {
      setContextInfo(termOrContext);
    }
    refreshSessions();
  }, [refreshSessions]);

  const closeTutor = useCallback(() => {
    setIsOpen(false);
    setCurrentTerm(null);
    setAgentStatus(DEFAULT_AGENT_STATUS);
  }, []);

  const sendMessage = useCallback(
    async (message, difficulty = 'beginner') => {
      if (!message.trim()) return;

      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      if (sessionId) setActiveSessionId(sessionId);
      setAgentStatus({
        phase: 'thinking',
        text: '질문을 분석 중입니다.',
      });

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      try {
        const response = await authFetch(`${API_BASE_URL}/api/v1/tutor/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            session_id: sessionId,
            message,
            difficulty,
            context_type: contextInfo?.type,
            context_id: contextInfo?.id,
            context_text: contextInfo?.stepContent,
          }),
        });

        if (!response.ok) throw new Error('Failed to get response');
        if (!response.body) throw new Error('Response body is empty');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;

            try {
              const data = JSON.parse(trimmed.slice(6));

              if (data.type === 'thinking') {
                setAgentStatus({
                  phase: 'thinking',
                  text: data.content || '질문을 분석 중입니다.',
                });
                continue;
              }

              if (data.type === 'tool_call') {
                setAgentStatus({
                  phase: 'tool_call',
                  text: `도구 실행 중: ${data.tool || '분석 도구'}`,
                  tool: data.tool || undefined,
                });
                continue;
              }

              if (data.content) {
                if (!fullContent) {
                  setAgentStatus({
                    phase: 'answering',
                    text: '답변을 생성 중입니다.',
                  });
                }
                fullContent += data.content;
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantMessage.id ? { ...m, content: fullContent } : m))
                );
              }

              if (data.session_id) {
                setSessionId(data.session_id);
                setActiveSessionId(data.session_id);
              }

              if (data.type === 'visualization' && (data.chartData || data.content)) {
                const vizMessage = {
                  id: Date.now() + Math.random(),
                  role: 'visualization',
                  content: data.content || null,
                  format: data.format || 'html',
                  chartData: data.chartData || null,
                  executionTime: data.execution_time_ms,
                  timestamp: new Date().toISOString(),
                };
                setMessages((prev) => [...prev, vizMessage]);
                continue;
              }

              if (data.type === 'done' && data.sources) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id ? { ...m, sources: data.sources } : m
                  )
                );
              }

              if (data.type === 'sources' && data.sources) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id ? { ...m, sources: data.sources } : m
                  )
                );
              }

              if (data.type === 'error' && data.error) {
                setAgentStatus({
                  phase: 'idle',
                  text: '응답 대기 중',
                });
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id
                      ? { ...m, content: `오류: ${data.error}`, isStreaming: false, isError: true }
                      : m
                  )
                );
              }

              if (data.type === 'done') {
                setAgentStatus({
                  phase: 'idle',
                  text: '응답 대기 중',
                });
              }
            } catch {
              // ignore malformed SSE chunk
            }
          }
        }

        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMessage.id ? { ...m, isStreaming: false } : m))
        );
      } catch (error) {
        console.error('Tutor error:', error);
        setAgentStatus({
          phase: 'idle',
          text: '응답 대기 중',
        });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? { ...m, content: '죄송합니다. 오류가 발생했습니다.', isStreaming: false, isError: true }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        setAgentStatus({
          phase: 'idle',
          text: '응답 대기 중',
        });
        refreshSessions();
      }
    },
    [sessionId, contextInfo, refreshSessions]
  );

  const createNewChat = useCallback(async () => {
    const created = await postJson(`${API_BASE_URL}/api/v1/tutor/sessions/new`, {});
    const nextSessionId = created?.session_id || null;

    setMessages([]);
    setCurrentTerm(null);
    setAgentStatus(DEFAULT_AGENT_STATUS);
    setSessionId(nextSessionId);
    setActiveSessionId(nextSessionId);

    await refreshSessions();
    return nextSessionId;
  }, [refreshSessions]);

  const deleteChat = useCallback(async (id) => {
    await deleteJson(`${API_BASE_URL}/api/v1/tutor/sessions/${id}`);

    if (activeSessionId === id) {
      setMessages([]);
      setSessionId(null);
      setCurrentTerm(null);
      setActiveSessionId(null);
      setAgentStatus(DEFAULT_AGENT_STATUS);
    }

    await refreshSessions();
  }, [activeSessionId, refreshSessions]);

  const loadChatHistory = useCallback(async (id) => {
    setActiveSessionId(id);

    const data = await fetchJson(`${API_BASE_URL}/api/v1/tutor/sessions/${id}/messages`);
    const loaded = (data.messages || []).map((message, index) => mapHistoryMessage(message, index));

    setMessages(loaded);
    setSessionId(id);
    setAgentStatus(DEFAULT_AGENT_STATUS);
  }, []);

  const requestVisualization = useCallback((query) => {
    sendMessage(`${query} (차트로 보여주세요)`, 'beginner');
  }, [sendMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setCurrentTerm(null);
    setActiveSessionId(null);
    setAgentStatus(DEFAULT_AGENT_STATUS);
  }, []);

  const value = useMemo(() => ({
    isOpen,
    openTutor,
    closeTutor,
    messages,
    isLoading,
    sendMessage,
    clearMessages,
    contextInfo,
    setContextInfo,
    currentTerm,
    setCurrentTerm,
    sessions,
    activeSessionId,
    createNewChat,
    deleteChat,
    loadChatHistory,
    refreshSessions,
    requestVisualization,
    agentStatus,
  }), [
    isOpen,
    openTutor,
    closeTutor,
    messages,
    isLoading,
    sendMessage,
    clearMessages,
    contextInfo,
    currentTerm,
    sessions,
    activeSessionId,
    createNewChat,
    deleteChat,
    loadChatHistory,
    refreshSessions,
    requestVisualization,
    agentStatus,
  ]);

  return (
    <TutorContext.Provider value={value}>
      {children}
    </TutorContext.Provider>
  );
}

export function useTutor() {
  const context = useContext(TutorContext);
  if (!context) throw new Error('useTutor must be used within a TutorProvider');
  return context;
}
