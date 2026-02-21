import { createContext, useContext, useState, useCallback } from 'react';
import { API_BASE_URL, fetchJson, postJson, deleteJson } from '../api/client';

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

    if (onCreated) onCreated(nextSessionId);
    await refreshSessions();
    return nextSessionId;
  }, [refreshSessions]);

  const deleteChat = useCallback(async (id, onDeleted) => {
    await deleteJson(`${API_BASE_URL}/api/v1/tutor/sessions/${id}`);

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
