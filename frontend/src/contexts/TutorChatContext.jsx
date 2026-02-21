import { createContext, useContext, useState, useCallback, startTransition } from 'react';
import { API_BASE_URL, authFetch } from '../api/client';

const TutorChatContext = createContext(null);

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

export function TutorChatProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    try {
      return localStorage.getItem('adelie_tutor_session') || null;
    } catch {
      return null;
    }
  });

  const sendMessage = useCallback(
    async (message, difficulty = 'beginner', contextInfo = null, setAgentStatus = null, onSessionCreated = null) => {
      if (!message.trim()) return;

      const DEFAULT_STATUS = { phase: 'idle', text: '응답 대기 중' };
      let hasError = false;

      const userMessage = {
        id: Date.now(),
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      if (setAgentStatus) setAgentStatus({ phase: 'thinking', text: '질문을 분석 중입니다.' });

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
          headers: { 'Content-Type': 'application/json' },
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
                if (setAgentStatus) setAgentStatus({ phase: 'thinking', text: data.content || '질문을 분석 중입니다.' });
                continue;
              }

              if (data.type === 'tool_call') {
                if (setAgentStatus) setAgentStatus({ phase: 'tool_call', text: `도구 실행 중: ${data.tool || '분석 도구'}`, tool: data.tool || undefined });
                continue;
              }

              if (data.content) {
                if (!fullContent && setAgentStatus) {
                  setAgentStatus({ phase: 'answering', text: '답변을 생성 중입니다.' });
                }
                fullContent += data.content;
                // SSE 청크 업데이트를 낮은 우선순위 트랜지션으로 처리
                startTransition(() => {
                  setMessages((prev) =>
                    prev.map((m) => (m.id === assistantMessage.id ? { ...m, content: fullContent } : m))
                  );
                });
              }

              if (data.session_id) {
                setSessionId(data.session_id);
                try { localStorage.setItem('adelie_tutor_session', data.session_id); } catch {}
                if (onSessionCreated) onSessionCreated(data.session_id);
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

              if ((data.type === 'done' || data.type === 'sources') && data.sources) {
                setMessages((prev) =>
                  prev.map((m) => (m.id === assistantMessage.id ? { ...m, sources: data.sources } : m))
                );
              }

              if (data.type === 'error' && data.error) {
                if (setAgentStatus) setAgentStatus(DEFAULT_STATUS);
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id
                      ? { ...m, content: `오류: ${data.error}`, isStreaming: false, isError: true }
                      : m
                  )
                );
              }

              if (data.type === 'done') {
                if (setAgentStatus) setAgentStatus(DEFAULT_STATUS);
              }
            } catch {
              // malformed SSE 청크 무시
            }
          }
        }

        setMessages((prev) =>
          prev.map((m) => (m.id === assistantMessage.id ? { ...m, isStreaming: false } : m))
        );
      } catch (error) {
        console.error('Tutor error:', error);
        hasError = true;
        if (setAgentStatus) setAgentStatus({ phase: 'error', text: '오류가 발생했습니다.' });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? { ...m, content: '죄송합니다. 오류가 발생했습니다.', isStreaming: false, isError: true }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        if (setAgentStatus && !hasError) setAgentStatus(DEFAULT_STATUS);
      }
    },
    [sessionId]
  );

  const loadChatHistory = useCallback(async (id, setActiveSessionId) => {
    if (setActiveSessionId) setActiveSessionId(id);

    const { fetchJson } = await import('../api/client');
    const data = await fetchJson(`${API_BASE_URL}/api/v1/tutor/sessions/${id}/messages`);
    const loaded = (data.messages || []).map((message, index) => mapHistoryMessage(message, index));

    setMessages(loaded);
    setSessionId(id);
    try { localStorage.setItem('adelie_tutor_session', id); } catch {}
  }, []);

  const clearMessages = useCallback(() => {
    setMessages((prev) => (prev.length > 0 ? [] : prev));
    setSessionId((prev) => (prev === null ? prev : null));
    try {
      if (localStorage.getItem('adelie_tutor_session') !== null) {
        localStorage.removeItem('adelie_tutor_session');
      }
    } catch {}
  }, []);

  return (
    <TutorChatContext.Provider value={{
      messages,
      isLoading,
      sessionId,
      setSessionId,
      sendMessage,
      loadChatHistory,
      clearMessages,
    }}>
      {children}
    </TutorChatContext.Provider>
  );
}

export function useTutorChat() {
  const ctx = useContext(TutorChatContext);
  if (!ctx) throw new Error('useTutorChat must be used within TutorChatProvider');
  return ctx;
}
