import { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { API_BASE_URL, authFetch, fetchJson, postJson, deleteJson } from '../api/client';
import { trackEvent } from '../utils/analytics';

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

const parseClarificationPayload = (content) => {
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

  if (message.message_type === 'clarification') {
    const parsed = parseClarificationPayload(message.content);
    return {
      id: `${message.id || Date.now()}-clarification-${index}`,
      role: 'clarification',
      content: parsed?.question || message.question || message.content,
      options: Array.isArray(parsed?.options) ? parsed.options : (Array.isArray(message.options) ? message.options : []),
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
  const [selectionCtaState, setSelectionCtaState] = useState({
    active: false,
    text: '',
    prompt: '',
    context: null,
  });
  const abortControllerRef = useRef(null);
  const isSubmittingSelectionRef = useRef(false);

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
    async (message, difficulty = 'beginner', options = {}) => {
      const { appendUser = true, contextOverride = null, analytics = null } = options;
      if (!message.trim()) return;
      const requestStartAt = Date.now();
      let hasError = false;

      if (appendUser) {
        const userMessage = {
          id: Date.now(),
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);
      }
      setIsLoading(true);
      if (sessionId) setActiveSessionId(sessionId);
      setAgentStatus({
        phase: 'thinking',
        text: '질문을 분석 중입니다.',
      });

      const assistantMsgId = Date.now() + 1;
      let assistantMsgCreated = false;
      let vizMsgId = null;
      let pendingSources = null;

      try {
        const controller = new AbortController();
        abortControllerRef.current = controller;

        const response = await authFetch(`${API_BASE_URL}/api/v1/tutor/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
          body: JSON.stringify({
            session_id: sessionId,
            message,
            difficulty,
            context_type: (contextOverride || contextInfo)?.type,
            context_id: (contextOverride || contextInfo)?.id,
            context_text: (contextOverride || contextInfo)?.stepContent,
          }),
        });

        if (!response.ok) {
          let errorMessage = '';
          try {
            const errorJson = await response.clone().json();
            if (typeof errorJson?.detail === 'string') {
              errorMessage = errorJson.detail;
            } else if (Array.isArray(errorJson?.detail)) {
              errorMessage = errorJson.detail
                .map((item) => item?.msg || item?.message || JSON.stringify(item))
                .join(', ');
            } else if (typeof errorJson?.error === 'string') {
              errorMessage = errorJson.error;
            }
          } catch {
            try {
              errorMessage = (await response.text()).trim();
            } catch {
              // ignore body parse errors
            }
          }

          throw new Error(errorMessage || `요청 실패 (${response.status})`);
        }
        if (!response.body) throw new Error('Response body is empty');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = '';

        const STREAM_FLUSH_INTERVAL_MS = 120;
        let lastFlushTime = Date.now();
        let pendingFlush = false;

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

              if (data.type === 'viz_intent') {
                setAgentStatus({
                  phase: 'tool_call',
                  text: '차트를 생성하고 있어요...',
                });
                const statusMessage = {
                  id: Date.now() + Math.random(),
                  role: 'assistant',
                  content: data.content || '📊 차트를 그려볼게요! 잠시만 기다려주세요.',
                  timestamp: new Date().toISOString(),
                  isStreaming: false,
                  isVizStatus: true,
                };
                setMessages((prev) => [...prev, statusMessage]);
                continue;
              }

              if (data.type === 'clarification' && data.question) {
                const clarificationMessage = {
                  id: Date.now() + Math.random(),
                  role: 'clarification',
                  content: data.question,
                  options: Array.isArray(data.options) ? data.options : [],
                  timestamp: new Date().toISOString(),
                  isStreaming: false,
                };
                setAgentStatus({
                  phase: 'idle',
                  text: '응답 대기 중',
                });
                setMessages((prev) => [...prev.filter((m) => !m.isVizStatus), clarificationMessage]);
                continue;
              }

              // Backend text chunks may come without an explicit type field.
              if ((data.type === 'text_delta' || (!data.type && data.content)) && data.content) {
                if (!fullContent) {
                  setAgentStatus({
                    phase: 'answering',
                    text: '답변을 생성 중입니다.',
                  });
                }
                fullContent += data.content;
                pendingFlush = true;

                if (!assistantMsgCreated) {
                  assistantMsgCreated = true;
                  const nextAssistant = {
                    id: assistantMsgId,
                    role: 'assistant',
                    content: fullContent,
                    timestamp: new Date().toISOString(),
                    isStreaming: true,
                  };
                  if (pendingSources) nextAssistant.sources = pendingSources;
                  setMessages((prev) => [...prev, nextAssistant]);
                  lastFlushTime = Date.now();
                  pendingFlush = false;
                }
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
                  title: data.title || '',
                  executionTime: data.execution_time_ms,
                  timestamp: new Date().toISOString(),
                };
                vizMsgId = vizMessage.id;
                // Insert BEFORE the current assistant text bubble (chart-first ordering)
                setMessages((prev) => {
                  if (!assistantMsgCreated) return [...prev, vizMessage];
                  const idx = prev.findIndex((m) => m.id === assistantMsgId);
                  if (idx === -1) return [...prev, vizMessage];
                  const next = [...prev];
                  next.splice(idx, 0, vizMessage);
                  return next;
                });
                continue;
              }

              if (data.type === 'done' && data.sources) {
                pendingSources = data.sources;
                setMessages((prev) =>
                  prev.map((m) => (
                    m.id === assistantMsgId || m.id === vizMsgId
                      ? { ...m, sources: data.sources }
                      : m
                  ))
                );
              }

              if (data.type === 'sources' && data.sources) {
                pendingSources = data.sources;
                setMessages((prev) =>
                  prev.map((m) => (
                    m.id === assistantMsgId || m.id === vizMsgId
                      ? { ...m, sources: data.sources }
                      : m
                  ))
                );
              }

              if (data.type === 'error' && data.error) {
                hasError = true;
                setAgentStatus({
                  phase: 'error',
                  text: data.error,
                });
                if (!assistantMsgCreated) {
                  assistantMsgCreated = true;
                  setMessages((prev) => [...prev, {
                    id: assistantMsgId,
                    role: 'assistant',
                    content: `오류: ${data.error}`,
                    timestamp: new Date().toISOString(),
                    isStreaming: false,
                    isError: true,
                  }]);
                } else {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId
                        ? { ...m, content: `오류: ${data.error}`, isStreaming: false, isError: true }
                        : m
                    )
                  );
                }
              }

              if (data.type === 'done') {
                if (!hasError) {
                  setAgentStatus({
                    phase: 'idle',
                    text: '응답 대기 중',
                  });
                }
                setMessages((prev) => prev.filter((m) => !m.isVizStatus));
              }
            } catch {
              // ignore malformed SSE chunk
            }
          }
          if (pendingFlush && Date.now() - lastFlushTime >= STREAM_FLUSH_INTERVAL_MS) {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantMsgId ? { ...m, content: fullContent } : m))
            );
            lastFlushTime = Date.now();
            pendingFlush = false;
          }
        }

        if (assistantMsgCreated) {
          setMessages((prev) =>
            prev.map((m) => (
              m.id === assistantMsgId
                ? {
                  ...m,
                  content: fullContent,
                  isStreaming: false,
                  ...(pendingSources ? { sources: pendingSources } : {}),
                }
                : m
            ))
          );
        }
        if (analytics?.source === 'selection_cta') {
          trackEvent('tutor_selection_success', {
            case_id: analytics.caseId ?? null,
            step_key: analytics.stepKey || null,
            selected_text_len: analytics.selectedTextLen || 0,
            difficulty: analytics.difficulty || difficulty,
            latency_ms: Date.now() - requestStartAt,
            response_len: fullContent.trim().length,
          });
        }
      } catch (error) {
        if (error?.name === 'AbortError') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, isStreaming: false, content: m.content || '(응답이 중단되었습니다.)' }
                : m
            )
          );
          return;
        }
        console.error('Tutor error:', error);
        const visibleErrorMessage = error?.message?.trim() || '죄송합니다. 오류가 발생했습니다.';
        hasError = true;
        if (analytics?.source === 'selection_cta') {
          trackEvent('tutor_selection_error', {
            case_id: analytics.caseId ?? null,
            step_key: analytics.stepKey || null,
            selected_text_len: analytics.selectedTextLen || 0,
            difficulty: analytics.difficulty || difficulty,
            latency_ms: Date.now() - requestStartAt,
            error_message: visibleErrorMessage.slice(0, 120),
          });
        }
        setAgentStatus({
          phase: 'error',
          text: visibleErrorMessage,
        });
        if (!assistantMsgCreated) {
          assistantMsgCreated = true;
          setMessages((prev) => [...prev, {
            id: assistantMsgId,
            role: 'assistant',
            content: `오류: ${visibleErrorMessage}`,
            timestamp: new Date().toISOString(),
            isStreaming: false,
            isError: true,
          }]);
        } else {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: `오류: ${visibleErrorMessage}`, isStreaming: false, isError: true }
                : m
            )
          );
        }
      } finally {
        abortControllerRef.current = null;
        setMessages((prev) => prev.filter((m) => !m.isVizStatus));
        setIsLoading(false);
        if (!hasError) {
          setAgentStatus({
            phase: 'idle',
            text: '응답 대기 중',
          });
        }
        refreshSessions();
      }
    },
    [sessionId, contextInfo, refreshSessions]
  );

  const stopGeneration = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const regenerateLastResponse = useCallback((difficulty = 'beginner') => {
    if (isLoading) return;

    const lastUser = [...messages].reverse().find((msg) => msg.role === 'user' && msg.content?.trim());
    if (!lastUser) return;

    setMessages((prev) => {
      const lastUserIndex = [...prev].map((m) => m.role).lastIndexOf('user');
      if (lastUserIndex < 0) return prev;
      return prev.slice(0, lastUserIndex + 1);
    });
    sendMessage(lastUser.content, difficulty, { appendUser: false });
  }, [isLoading, messages, sendMessage]);

  const updateSelectionCtaState = useCallback((nextState) => {
    setSelectionCtaState((prev) => ({
      ...prev,
      ...nextState,
    }));
  }, []);

  const clearSelectionCtaState = useCallback(() => {
    setSelectionCtaState({
      active: false,
      text: '',
      prompt: '',
      context: null,
    });
  }, []);

  const askTutorFromSelection = useCallback(async (difficulty = 'beginner') => {
    const prompt = selectionCtaState.prompt?.trim();
    if (!selectionCtaState.active || !prompt || isSubmittingSelectionRef.current) return;

    isSubmittingSelectionRef.current = true;
    try {
      const selectionContext = selectionCtaState.context || null;
      const selectedTextLen = selectionCtaState.text?.trim()?.length || 0;
      const normalizedCaseId = Number(selectionContext?.id);
      const safeCaseId = Number.isFinite(normalizedCaseId) ? normalizedCaseId : null;
      trackEvent('tutor_selection_submit', {
        case_id: safeCaseId,
        step_key: selectionContext?.stepKey || null,
        selected_text_len: selectedTextLen,
        difficulty,
      });

      openTutor(selectionContext);
      await sendMessage(
        prompt,
        difficulty,
        {
          contextOverride: selectionContext,
          analytics: {
            source: 'selection_cta',
            caseId: safeCaseId,
            stepKey: selectionContext?.stepKey || null,
            selectedTextLen,
            difficulty,
          },
        },
      );
    } finally {
      isSubmittingSelectionRef.current = false;
      clearSelectionCtaState();
      try {
        window.getSelection?.()?.removeAllRanges();
        window.dispatchEvent(new Event('narrative-selection-clear'));
      } catch {
        // ignore selection clear failures
      }
    }
  }, [selectionCtaState, openTutor, sendMessage, clearSelectionCtaState]);

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
    stopGeneration,
    regenerateLastResponse,
    selectionCtaState,
    updateSelectionCtaState,
    clearSelectionCtaState,
    askTutorFromSelection,
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
    stopGeneration,
    regenerateLastResponse,
    selectionCtaState,
    updateSelectionCtaState,
    clearSelectionCtaState,
    askTutorFromSelection,
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
