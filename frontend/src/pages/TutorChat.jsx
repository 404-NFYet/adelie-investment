/**
 * TutorChat.jsx - AI 튜터 대화 내역 페이지
 * 세션 목록 + 새 대화 버튼 + 세션 선택 시 TutorModal 열기
 */
import { useState, useEffect } from 'react';
import { useTutor } from '../contexts';
import { API_BASE_URL } from '../config';
import AppHeader from '../components/layout/AppHeader';

export default function TutorChat() {
  const { openTutor, createNewChat, loadChatHistory, deleteChat } = useTutor();
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // 세션 목록 가져오기
  useEffect(() => {
    setIsLoading(true);
    fetch(`${API_BASE_URL}/api/v1/tutor/sessions`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setSessions(data.sessions || data || []))
      .catch(() => setSessions([]))
      .finally(() => setIsLoading(false));
  }, []);

  const handleNewChat = () => {
    createNewChat();
    openTutor();
  };

  const handleSelectSession = (session) => {
    loadChatHistory(session.session_id || session.id);
    openTutor();
  };

  const handleDeleteSession = async (e, session) => {
    e.stopPropagation();
    const id = session.session_id || session.id;
    try {
      await fetch(`${API_BASE_URL}/api/v1/tutor/sessions/${id}`, { method: 'DELETE' });
      setSessions(prev => prev.filter(s => (s.session_id || s.id) !== id));
      deleteChat(id);
    } catch {}
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    if (diff < 60000) return '방금 전';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;
    return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader title="AI 튜터" />

      <div className="max-w-mobile mx-auto px-4 pt-4">
        {/* 새 대화 버튼 */}
        <button
          onClick={handleNewChat}
          className="w-full py-3.5 rounded-2xl bg-primary text-white font-semibold text-sm hover:bg-primary-hover transition-colors mb-6 flex items-center justify-center gap-2"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          새 대화 시작
        </button>

        {/* 세션 목록 */}
        {isLoading ? (
          <div className="text-center py-12 text-text-secondary text-sm">불러오는 중...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-text-secondary text-sm mb-1">대화 내역이 없습니다</p>
            <p className="text-text-muted text-xs">새 대화를 시작해보세요</p>
          </div>
        ) : (
          <div className="space-y-2">
            <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">이전 대화</h2>
            {sessions.map((session) => {
              const id = session.session_id || session.id;
              return (
                <div
                  key={id}
                  onClick={() => handleSelectSession(session)}
                  className="p-4 rounded-2xl bg-surface-elevated border border-border hover:border-primary/30 transition-all cursor-pointer group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {session.title || session.last_message || '대화'}
                      </p>
                      {session.message_count > 0 && (
                        <p className="text-xs text-text-muted mt-1">
                          {session.message_count}개 메시지
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs text-text-muted">
                        {formatDate(session.updated_at || session.created_at)}
                      </span>
                      <button
                        onClick={(e) => handleDeleteSession(e, session)}
                        className="opacity-0 group-hover:opacity-100 w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-error hover:bg-error-light transition-all"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
