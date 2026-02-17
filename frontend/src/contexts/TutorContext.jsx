import { createContext, useContext, useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config';

const TutorContext = createContext(null);
const SESSION_KEY = 'adelie_tutor_session';

/** SSE 스트리밍 최대 재시도 횟수 */
const MAX_RETRIES = 2;
/** 재시도 대기 시간 (ms) */
const RETRY_DELAY = 1500;

export function TutorProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    try { return localStorage.getItem(SESSION_KEY) || null; } catch { return null; }
  });
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [contextInfo, setContextInfo] = useState(null);
  const [currentTerm, setCurrentTerm] = useState(null);

  // 재시도 관련 상태
  const [lastFailedMessage, setLastFailedMessage] = useState(null);
  const [lastFailedDifficulty, setLastFailedDifficulty] = useState(null);
  const retryCountRef = useRef(0);

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

  /**
   * SSE 스트리밍 메시지 전송.
   * 실패 시 자동 재시도(MAX_RETRIES)하고, 재시도 소진 시 "다시 시도" 버튼을 표시한다.
   */
  const sendMessage = useCallback(
    async (message, difficulty = 'beginner', _isRetry = false) => {
      if (!message.trim()) return;

      // 재시도가 아닐 때만 사용자 메시지 추가
      if (!_isRetry) {
        retryCountRef.current = 0;
        setLastFailedMessage(null);
        setLastFailedDifficulty(null);

        const userMessage = {
          id: Date.now(),
          role: 'user',
          content: message,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);
      }

      setIsLoading(true);

      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };

      // 재시도 시 기존 에러 메시지 제거 후 새 assistant 메시지 추가
      if (_isRetry) {
        setMessages((prev) => {
          // 마지막 에러 메시지 제거
          const filtered = prev.filter((m) => !(m.isError && m.role === 'assistant'));
          return [...filtered, assistantMessage];
        });
      } else {
        setMessages((prev) => [...prev, assistantMessage]);
      }

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

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullContent = '';
        let buffer = ''; // 불완전 청크 버퍼
        let receivedData = false; // 실제 데이터 수신 여부

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
              if (data.content && data.type !== 'visualization') {
                receivedData = true;
                fullContent += data.content;
                setMessages((prev) =>
                  prev.map((m) => m.id === assistantMessage.id ? { ...m, content: fullContent } : m)
                );
              }

              // done: 세션 ID 업데이트
              if (data.session_id) setSessionId(data.session_id);

              // visualization: 차트 렌더링 (JSON chartData 우선, HTML 폴백)
              if (data.type === 'visualization' && (data.chartData || data.content)) {
                receivedData = true;
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

              // error: SSE 내부 에러 이벤트
              if (data.type === 'error' && data.error) {
                throw new Error(data.error);
              }
            } catch (parseErr) {
              // error 이벤트에서 throw된 것은 다시 throw
              if (parseErr.message && !parseErr.message.includes('JSON')) {
                throw parseErr;
              }
              // JSON 파싱 실패 -- 불완전 데이터, 무시
            }
          }
        }

        // 스트리밍 완료 — 데이터를 받지 못한 경우 에러 처리
        if (!receivedData && !fullContent) {
          throw new Error('응답을 받지 못했습니다.');
        }

        // 성공 — 재시도 카운터 초기화
        retryCountRef.current = 0;
        setLastFailedMessage(null);
        setLastFailedDifficulty(null);

        setMessages((prev) =>
          prev.map((m) => m.id === assistantMessage.id ? { ...m, isStreaming: false } : m)
        );
      } catch (error) {
        console.error('Tutor error:', error);

        // 자동 재시도 (MAX_RETRIES 이내)
        if (retryCountRef.current < MAX_RETRIES) {
          retryCountRef.current += 1;
          console.log(`SSE 재시도 ${retryCountRef.current}/${MAX_RETRIES}...`);

          // 에러 메시지 제거
          setMessages((prev) => prev.filter((m) => m.id !== assistantMessage.id));
          setIsLoading(false);

          await new Promise((r) => setTimeout(r, RETRY_DELAY));
          return sendMessage(message, difficulty, true);
        }

        // 재시도 소진 — 에러 메시지 + "다시 시도" 버튼 표시
        setLastFailedMessage(message);
        setLastFailedDifficulty(difficulty);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessage.id
              ? {
                  ...m,
                  content: '죄송합니다. 응답을 받는 데 실패했습니다.',
                  isStreaming: false,
                  isError: true,
                  canRetry: true,
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, contextInfo]
  );

  /** 마지막 실패한 메시지 재시도 */
  const retryLastMessage = useCallback(() => {
    if (!lastFailedMessage) return;
    retryCountRef.current = 0;
    sendMessage(lastFailedMessage, lastFailedDifficulty || 'beginner', true);
  }, [lastFailedMessage, lastFailedDifficulty, sendMessage]);

  // 세션 관리
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);

  const createNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setCurrentTerm(null);
    setActiveSessionId(null);
    setLastFailedMessage(null);
    setLastFailedDifficulty(null);
    retryCountRef.current = 0;
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
    } catch (err) {
      console.error('대화 히스토리 로드 실패:', err);
    }
  }, []);

  const requestVisualization = useCallback((query) => {
    // 시각화 요청을 챗봇 메시지로 전달
    sendMessage(`${query} (차트로 보여주세요)`, 'beginner');
  }, [sendMessage]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setCurrentTerm(null);
    setLastFailedMessage(null);
    setLastFailedDifficulty(null);
    retryCountRef.current = 0;
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
    requestVisualization,
    retryLastMessage,
    lastFailedMessage,
  }), [
    isOpen, openTutor, closeTutor, messages, isLoading, sendMessage,
    clearMessages, contextInfo, currentTerm, sessions, activeSessionId,
    createNewChat, deleteChat, loadChatHistory, requestVisualization,
    retryLastMessage, lastFailedMessage,
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
