import { createContext, useContext, useState, useCallback, startTransition } from 'react';
import { API_BASE_URL, authFetch } from '../api/client';

const TutorChatContext = createContext(null);
const STREAM_FLUSH_INTERVAL_MS = 240;

const parseVisualizationPayload = (content) => {
  if (!content) return null;
  if (typeof content === 'object') return content;
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
};

function sanitizeStreamDelta(delta) {
  if (typeof delta !== 'string') return '';

  const cleaned = delta
    .replace(/<\|[^>]+\|>/g, '')
    .replace(/\r/g, '')
    .replace(/\u0000/g, '');

  const trimmed = cleaned.trim();
  if (!trimmed) return cleaned;

  if (/^```(?:\w+)?$/i.test(trimmed)) return '';
  if (/^\|{1,5}$/.test(trimmed)) return '';
  if (/^\|\s*$/.test(trimmed)) return '';
  if (/^(assistant|user|system)\s*[:|]$/i.test(trimmed)) return '';

  return cleaned;
}

function extractFlushableText(buffer, force = false) {
  if (!buffer) return { flush: '', remain: '' };
  if (force) return { flush: buffer, remain: '' };

  let boundary = -1;
  for (let idx = 0; idx < buffer.length; idx += 1) {
    const char = buffer[idx];
    if (char === '\n' || char === '.' || char === '!' || char === '?' || char === '。' || char === '！' || char === '？') {
      boundary = idx + 1;
    }
  }

  if (boundary === -1) {
    if (buffer.length < 64) return { flush: '', remain: buffer };

    const whitespace = buffer.lastIndexOf(' ', 56);
    boundary = whitespace > 16 ? whitespace + 1 : 56;
  }

  return {
    flush: buffer.slice(0, boundary),
    remain: buffer.slice(boundary),
  };
}

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
    sources: message.sources || null,
    uiActions: message.ui_actions || null,
    model: message.model || null,
    structured: message.structured || null,
    guardrailNotice: message.guardrail_notice || null,
    guardrailDecision: message.guardrail_decision || null,
    guardrailMode: message.guardrail_mode || null,
  };
};

function buildAssistantTurns(messages = []) {
  let latestUserPrompt = '';
  const turns = [];

  messages.forEach((message, index) => {
    if (message?.role === 'user') {
      latestUserPrompt = typeof message.content === 'string' ? message.content : '';
      return;
    }

    if (message?.role !== 'assistant') return;

    turns.push({
      id: message.turnId || `turn-${message.id || index}`,
      assistantMessageId: message.id,
      userPrompt: latestUserPrompt,
      assistantText: typeof message.content === 'string' ? message.content : '',
      status: 'done',
      createdAt: message.timestamp || new Date().toISOString(),
      sources: Array.isArray(message.sources) ? message.sources : [],
      uiActions: Array.isArray(message.uiActions) ? message.uiActions : [],
      model: message.model || null,
      structured: message.structured || null,
      guardrailNotice: message.guardrailNotice || null,
      guardrailDecision: message.guardrailDecision || null,
      guardrailMode: message.guardrailMode || null,
    });
  });

  return turns;
}

function updateTurnById(previousTurns, turnId, updater) {
  return previousTurns.map((turn) => {
    if (turn.id !== turnId) return turn;
    return updater(turn);
  });
}

export function TutorChatProvider({ children }) {
  const [messages, setMessages] = useState([]);
  const [assistantTurns, setAssistantTurns] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    try {
      return localStorage.getItem('adelie_tutor_session') || null;
    } catch {
      return null;
    }
  });

  const sendMessage = useCallback(
    async (
      message,
      difficulty = 'beginner',
      contextInfo = null,
      setAgentStatus = null,
      onSessionCreated = null,
      options = {},
    ) => {
      if (!message.trim()) return;

      const DEFAULT_STATUS = { phase: 'idle', text: '응답 대기 중' };
      let hasError = false;
      let pendingSources = [];
      let pendingUiActions = [];
      let pendingModel = null;
      let pendingStructured = null;
      let pendingGuardrailNotice = null;
      let pendingGuardrailDecision = null;
      let pendingGuardrailMode = null;
      let pendingBuffer = '';
      let renderedContent = '';
      let lastFlushAt = Date.now();
      const normalizedOptions = {
        useWebSearch: Boolean(options?.useWebSearch),
        responseMode: options?.responseMode || 'plain',
        structuredExtract: Boolean(options?.structuredExtract),
      };

      const turnId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      const userMessage = {
        id: `${Date.now()}-user`,
        turnId,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      if (setAgentStatus) setAgentStatus({ phase: 'thinking', text: '질문을 분석 중입니다.' });

      const assistantMessage = {
        id: `${Date.now()}-assistant`,
        turnId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
        structured: null,
        guardrailNotice: null,
        guardrailDecision: null,
        guardrailMode: null,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setAssistantTurns((prev) => [
        ...prev,
        {
          id: turnId,
          assistantMessageId: assistantMessage.id,
          userPrompt: message,
          assistantText: '',
          status: 'streaming',
          createdAt: assistantMessage.timestamp,
          sources: [],
          uiActions: [],
          model: null,
          structured: null,
          guardrailNotice: null,
          guardrailDecision: null,
          guardrailMode: null,
        },
      ]);

      const syncAssistantState = (nextContent, options = {}) => {
        const {
          isStreaming = true,
          isError = false,
          sources = pendingSources,
          uiActions = pendingUiActions,
          model = pendingModel,
          structured = pendingStructured,
          guardrailNotice = pendingGuardrailNotice,
          guardrailDecision = pendingGuardrailDecision,
          guardrailMode = pendingGuardrailMode,
          status = 'streaming',
        } = options;

        startTransition(() => {
          setMessages((prev) =>
            prev.map((item) => {
              if (item.id !== assistantMessage.id) return item;
              return {
                ...item,
                content: nextContent,
                isStreaming,
                isError,
                sources,
                uiActions,
                model,
                structured,
                guardrailNotice,
                guardrailDecision,
                guardrailMode,
              };
            })
          );
        });

        setAssistantTurns((prev) =>
          updateTurnById(prev, turnId, (turn) => ({
            ...turn,
            assistantText: nextContent,
            status,
            sources,
            uiActions,
            model,
            structured,
            guardrailNotice,
            guardrailDecision,
            guardrailMode,
          }))
        );
      };

      const flushBuffer = (force = false) => {
        const { flush, remain } = extractFlushableText(pendingBuffer, force);
        if (!flush && !force) return;

        renderedContent += flush;
        pendingBuffer = remain;

        if (force && pendingBuffer) {
          renderedContent += pendingBuffer;
          pendingBuffer = '';
        }

        syncAssistantState(renderedContent, {
          isStreaming: true,
          status: 'streaming',
        });
      };

      const processSseLine = (line, eventName = '') => {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) return;

        try {
          const data = JSON.parse(trimmed.slice(6));
          const normalizedEventType = data.type || eventName || '';

          if (!data.type && normalizedEventType) {
            data.type = normalizedEventType;
          }

          if (data.session_id) {
            setSessionId(data.session_id);
            try { localStorage.setItem('adelie_tutor_session', data.session_id); } catch {}
            if (onSessionCreated) onSessionCreated(data.session_id);
          }

          if (data.type === 'thinking') {
            if (setAgentStatus) {
              setAgentStatus({ phase: 'thinking', text: data.content || '질문을 분석 중입니다.' });
            }
            return;
          }

          if (data.type === 'tool_call') {
            if (setAgentStatus) {
              setAgentStatus({ phase: 'tool_call', text: `도구 실행 중: ${data.tool || '분석 도구'}`, tool: data.tool || undefined });
            }
            return;
          }

          if (data.type === 'guardrail_notice') {
            pendingGuardrailNotice = typeof data.content === 'string' ? data.content : null;
            pendingGuardrailDecision = typeof data.guardrail_decision === 'string' ? data.guardrail_decision : pendingGuardrailDecision;
            pendingGuardrailMode = typeof data.guardrail_mode === 'string' ? data.guardrail_mode : pendingGuardrailMode;
            if (setAgentStatus && pendingGuardrailNotice) {
              setAgentStatus({ phase: 'notice', text: pendingGuardrailNotice });
            }
            syncAssistantState(renderedContent, {
              isStreaming: true,
              status: 'streaming',
              guardrailNotice: pendingGuardrailNotice,
              guardrailDecision: pendingGuardrailDecision,
              guardrailMode: pendingGuardrailMode,
            });
            return;
          }

          if (data.type === 'sources' && Array.isArray(data.sources)) {
            pendingSources = data.sources;
            return;
          }

          if (data.type === 'ui_action' && Array.isArray(data.actions)) {
            pendingUiActions = data.actions;
            syncAssistantState(renderedContent, {
              isStreaming: true,
              status: 'streaming',
              uiActions: pendingUiActions,
            });
            return;
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
            return;
          }

          if (data.type === 'error' && data.error) {
            hasError = true;
            flushBuffer(true);
            const errorText = renderedContent || `오류: ${data.error}`;
            if (setAgentStatus) setAgentStatus({ phase: 'error', text: '오류가 발생했습니다.' });
            syncAssistantState(errorText, {
              isStreaming: false,
              isError: true,
              status: 'error',
            });
            return;
          }

          if (data.type === 'done') {
            if (Array.isArray(data.sources)) {
              pendingSources = data.sources;
            }
            if (Array.isArray(data.actions)) {
              pendingUiActions = data.actions;
            }
            if (typeof data.model === 'string' && data.model.trim()) {
              pendingModel = data.model.trim();
            }
            if (data.structured && typeof data.structured === 'object') {
              pendingStructured = data.structured;
            }
            if (typeof data.guardrail_decision === 'string') {
              pendingGuardrailDecision = data.guardrail_decision;
            }
            if (typeof data.guardrail_mode === 'string') {
              pendingGuardrailMode = data.guardrail_mode;
            }

            flushBuffer(true);
            syncAssistantState(renderedContent, {
              isStreaming: false,
              status: hasError ? 'error' : 'done',
            });
            if (setAgentStatus && !hasError) setAgentStatus(DEFAULT_STATUS);
            return;
          }

          if (typeof data.content === 'string') {
            const sanitized = sanitizeStreamDelta(data.content);
            if (!sanitized) return;

            if (!renderedContent && setAgentStatus) {
              setAgentStatus({ phase: 'answering', text: '답변을 생성 중입니다.' });
            }

            pendingBuffer += sanitized;

            const now = Date.now();
            const shouldFlush = /[.!?。！？\n]/.test(sanitized)
              || (pendingBuffer.length >= 14 && now - lastFlushAt >= STREAM_FLUSH_INTERVAL_MS);

            if (shouldFlush) {
              flushBuffer(false);
              lastFlushAt = now;
            }
          }
        } catch {
          // malformed SSE chunk 무시
        }
      };

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
            use_web_search: normalizedOptions.useWebSearch,
            response_mode: normalizedOptions.responseMode,
            structured_extract: normalizedOptions.structuredExtract,
          }),
        });

        if (!response.ok) throw new Error('Failed to get response');
        if (!response.body) throw new Error('Response body is empty');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamBuffer = '';
        let currentEventName = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          streamBuffer += decoder.decode(value, { stream: true });
          const lines = streamBuffer.split('\n');
          streamBuffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('event:')) {
              currentEventName = trimmed.slice(6).trim();
              continue;
            }

            processSseLine(line, currentEventName);
            if (!trimmed) {
              currentEventName = '';
            }
          }
        }

        const remaining = `${streamBuffer}${decoder.decode()}`;
        if (remaining.trim()) {
          remaining.split('\n').forEach((line) => {
            const trimmed = line.trim();
            if (trimmed.startsWith('event:')) {
              currentEventName = trimmed.slice(6).trim();
              return;
            }
            processSseLine(line, currentEventName);
            if (!trimmed) {
              currentEventName = '';
            }
          });
        }

        flushBuffer(true);

        syncAssistantState(renderedContent, {
          isStreaming: false,
          isError: hasError,
          status: hasError ? 'error' : 'done',
        });
      } catch (error) {
        console.error('Tutor error:', error);
        hasError = true;
        if (setAgentStatus) setAgentStatus({ phase: 'error', text: '오류가 발생했습니다.' });

        const fallbackText = renderedContent || '죄송합니다. 오류가 발생했습니다.';
        syncAssistantState(fallbackText, {
          isStreaming: false,
          isError: true,
          status: 'error',
        });
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
    setAssistantTurns(buildAssistantTurns(loaded));
    setSessionId(id);
    try { localStorage.setItem('adelie_tutor_session', id); } catch {}
  }, []);

  const clearMessages = useCallback(() => {
    setMessages((prev) => (prev.length > 0 ? [] : prev));
    setAssistantTurns((prev) => (prev.length > 0 ? [] : prev));
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
      assistantTurns,
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
