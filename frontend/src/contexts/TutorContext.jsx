import { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { API_BASE_URL } from '../config';

const TutorContext = createContext(null);
const SESSION_KEY = 'adelie_tutor_session';

export function TutorProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    try { return localStorage.getItem(SESSION_KEY) || null; } catch { return null; }
  });
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [contextInfo, setContextInfo] = useState(null);
  const [currentTerm, setCurrentTerm] = useState(null);

  // sessionId를 localStorage에 저장
  useEffect(() => {
    try {
      if (sessionId) localStorage.setItem(SESSION_KEY, sessionId);
      else localStorage.removeItem(SESSION_KEY);
    } catch {}
  }, [sessionId]);

  const openTutor = useCallback((termOrContext = null) => {
    setIsOpen(true);
    if (typeof termOrContext === 'string') {
      setCurrentTerm(termOrContext);
    } else if (termOrContext) {
      setContextInfo(termOrContext);
    }
  }, []);

  const closeTutor = useCallback(() => {
    setIsOpen(false);
    setCurrentTerm(null);
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

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE_URL}/api/v1/tutor/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            session_id: sessionId,
            message,
            difficulty,
            context_type: contextInfo?.type,
            context_id: contextInfo?.id,
          }),
        });

        if (!response.ok) throw new Error('Failed to get response');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = ''; // 불완전 청크 버퍼

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          // 마지막 라인이 불완전할 수 있으므로 버퍼에 유지
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;

            try {
              const data = JSON.parse(trimmed.slice(6));

              // thinking/tool_call 이벤트는 무시 (펭귄 모션 그래픽으로 대체)
              if (data.type === 'thinking' || data.type === 'tool_call') {
                continue;
              }

              // text_delta: 스트리밍 텍스트 누적
              if (data.content) {
                fullContent += data.content;
                setMessages((prev) =>
                  prev.map((m) => m.id === assistantMessage.id ? { ...m, content: fullContent } : m)
                );
              }

              // done: 세션 ID 업데이트
              if (data.session_id) setSessionId(data.session_id);

              // visualization: 차트 렌더링 (JSON chartData 우선, HTML 폴백)
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

              // done: sources 수집
              if (data.type === 'done' && data.sources) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id ? { ...m, sources: data.sources } : m
                  )
                );
              }

              // sources 별도 이벤트 (tutor_engine 경유 시)
              if (data.type === 'sources' && data.sources) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id ? { ...m, sources: data.sources } : m
                  )
                );
              }

              // error: 에러 표시
              if (data.type === 'error' && data.error) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessage.id
                      ? { ...m, content: `오류: ${data.error}`, isStreaming: false, isError: true }
                      : m
                  )
                );
              }
            } catch (e) {
              // JSON 파싱 실패 -- 불완전 데이터, 무시
            }
          }
        }

        setMessages((prev) =>
          prev.map((m) => m.id === assistantMessage.id ? { ...m, isStreaming: false } : m)
        );
      } catch (error) {
        console.error('Tutor error:', error);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? { ...m, content: '죄송합니다. 오류가 발생했습니다.', isStreaming: false, isError: true }
              : m
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, contextInfo]
  );

  // 세션 관리
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);

  const createNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setCurrentTerm(null);
    setActiveSessionId(null);
  }, []);

  const deleteChat = useCallback((id) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      createNewChat();
    }
  }, [activeSessionId, createNewChat]);

  const loadChatHistory = useCallback(async (id) => {
    setActiveSessionId(id);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/tutor/sessions/${id}/messages`);
      if (!res.ok) return;
      const data = await res.json();
      const loaded = (data.messages || []).map((m, i) => ({
        id: Date.now() + i,
        role: m.role,
        content: m.content,
        timestamp: m.created_at,
        isStreaming: false,
      }));
      setMessages(loaded);
      setSessionId(id);
    } catch {}
  }, []);

  const requestVisualization = useCallback((query) => {
    // 시각화 요청을 챗봇 메시지로 전달
    sendMessage(`${query} (차트로 보여주세요)`, 'beginner');
  }, [sendMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setCurrentTerm(null);
  }, []);

  // 추천 질문 관리
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    if (!contextInfo?.type || !contextInfo?.id) {
      setSuggestions([]);
      return;
    }

    const fetchSuggestions = async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE_URL}/api/v1/tutor/suggestions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            context_type: contextInfo.type,
            context_id: Number(contextInfo.id),
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data.suggestions || []);
        }
      } catch (e) {
        console.error('Failed to fetch suggestions:', e);
      }
    };

    fetchSuggestions();
  }, [contextInfo]);

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
    requestVisualization,
    suggestions,
  }), [
    isOpen, openTutor, closeTutor, messages, isLoading, sendMessage,
    clearMessages, contextInfo, currentTerm, sessions, activeSessionId,
    createNewChat, deleteChat, loadChatHistory, requestVisualization,
    suggestions,
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
