import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { API_BASE_URL, fetchJson, postJson, deleteJson } from '../api/client';
import { removeSessionCardMeta } from '../utils/agent/sessionCardMetaStore';
import { trackEvent, TRACK_EVENTS } from '../utils/analytics';

const TutorSessionContext = createContext(null);

const SESSION_KEY = 'adelie_tutor_session';

export function TutorSessionProvider({ children }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      return localStorage.getItem(SESSION_KEY) || null;
    } catch {
      return null;
    }
  });

  // 세션 복원 시 서버 유효성 검증
  const validateSession = useCallback(async (sessionId) => {
    try {
      const res = await fetchJson(`${API_BASE_URL}/api/v1/tutor/sessions/${sessionId}`);
      return !!res;
    } catch {
      return false;
    }
  }, []);

  // localStorage에서 복원된 세션이 서버에 존재하는지 확인
  useEffect(() => {
    if (!activeSessionId) return;
    validateSession(activeSessionId).then((isValid) => {
      if (!isValid) {
        setActiveSessionId(null);
        try { localStorage.removeItem(SESSION_KEY); } catch {}
      }
    });
  }, []); // 마운트 시 1회만 실행

  const refreshSessions = useCallback(async () => {
    try {
      const sessionList = await fetchJson(`${API_BASE_URL}/api/v1/tutor/sessions`);
      setSessions(Array.isArray(sessionList) ? sessionList : []);
    } catch (error) {
      console.error('세션 목록 조회 실패:', error);
      setSessions([]);
    }
  }, []);

  const createNewChat = useCallback(async (onCreated) => {
    const created = await postJson(`${API_BASE_URL}/api/v1/tutor/sessions/new`, {});
    const nextSessionId = created?.session_id || null;

    setActiveSessionId(nextSessionId);
    try {
      if (nextSessionId) localStorage.setItem(SESSION_KEY, nextSessionId);
      else localStorage.removeItem(SESSION_KEY);
    } catch {}

    // 세션 생성 트래킹
    trackEvent(TRACK_EVENTS.TUTOR_SESSION_CREATE, { session_id: nextSessionId });

    if (onCreated) onCreated(nextSessionId);
    await refreshSessions();
    return nextSessionId;
  }, [refreshSessions]);

  const deleteChat = useCallback(async (id, onDeleted) => {
    await deleteJson(`${API_BASE_URL}/api/v1/tutor/sessions/${id}`);

    // 삭제된 세션의 카드 메타(localStorage) 정리
    removeSessionCardMeta(id);

    if (activeSessionId === id) {
      setActiveSessionId(null);
      try { localStorage.removeItem(SESSION_KEY); } catch {}
      if (onDeleted) onDeleted();
    }

    await refreshSessions();
  }, [activeSessionId, refreshSessions]);

  return (
    <TutorSessionContext.Provider value={{
      sessions,
      activeSessionId,
      setActiveSessionId,
      refreshSessions,
      createNewChat,
      deleteChat,
    }}>
      {children}
    </TutorSessionContext.Provider>
  );
}

export function useTutorSession() {
  const ctx = useContext(TutorSessionContext);
  if (!ctx) throw new Error('useTutorSession must be used within TutorSessionProvider');
  return ctx;
}
