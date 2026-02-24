import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useTutor } from '../contexts';
import ReviewCard from '../components/domain/ReviewCard';
import { formatRelativeDate } from '../utils/dateFormat';

export default function AgentHistoryPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    sessions,
    activeSessionId,
    refreshSessions,
    loadChatHistory,
    deleteChat,
  } = useTutor();

  const [openingSessionId, setOpeningSessionId] = useState(null);
  const [deletingSessionId, setDeletingSessionId] = useState(null);
  const [expandedReviewId, setExpandedReviewId] = useState(null);

  const mode = location.state?.mode || 'home';
  const contextPayload = location.state?.contextPayload || null;

  const safeSessions = useMemo(() => (Array.isArray(sessions) ? sessions : []), [sessions]);

  // 핀 고정 + 복습 요약이 있는 세션
  const pinnedSessions = useMemo(
    () => safeSessions.filter((s) => s.is_pinned && s.review_summary),
    [safeSessions],
  );

  // 나머지 세션 (핀 미고정 또는 복습 요약 없음)
  const regularSessions = useMemo(
    () => safeSessions.filter((s) => !(s.is_pinned && s.review_summary)),
    [safeSessions],
  );

  useEffect(() => {
    refreshSessions().catch(() => {});
  }, [refreshSessions]);

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
      return;
    }

    navigate('/agent', {
      replace: true,
      state: {
        mode,
        contextPayload,
      },
    });
  };

  const openSession = async (sessionId) => {
    setOpeningSessionId(sessionId);

    try {
      await loadChatHistory(sessionId);
      navigate('/agent', {
        state: {
          mode,
          contextPayload,
          sessionId,
          resetConversation: false,
        },
      });
    } catch {
      // ignore
    } finally {
      setOpeningSessionId(null);
    }
  };

  const removeSession = async (sessionId) => {
    setDeletingSessionId(sessionId);

    try {
      await deleteChat(sessionId);
      await refreshSessions();
    } catch {
      // ignore
    } finally {
      setDeletingSessionId(null);
    }
  };

  // ReviewCard 핸들러: 다시 대화하기
  const handleResumeChat = (session) => {
    openSession(session.id);
  };

  // ReviewCard 핸들러: 전체 보기 (세션 메시지 로드 후 에이전트 이동)
  const handleViewFull = (session) => {
    openSession(session.id);
  };

  const renderSessionRow = (session, { isPinned = false } = {}) => {
    const isOpening = openingSessionId === session.id;
    const isDeleting = deletingSessionId === session.id;
    const isActive = activeSessionId === session.id;
    const isExpanded = expandedReviewId === session.id;

    return (
      <div key={session.id} className="space-y-2">
        <div
          className={`w-full rounded-2xl border bg-white px-4 py-3 transition-colors ${
            isActive ? 'border-[#ffb089] bg-[#fff8f5]' : 'border-[#f3f4f6]'
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <button
              type="button"
              onClick={() => {
                if (isPinned) {
                  setExpandedReviewId((prev) => (prev === session.id ? null : session.id));
                } else {
                  openSession(session.id);
                }
              }}
              className="min-w-0 flex-1 text-left"
            >
              <div className="flex items-center gap-2">
                {isPinned && (
                  <span className="inline-flex items-center rounded-full bg-[#FFF2E8] px-2 py-0.5 text-[10px] font-semibold text-[#FF6B00]">
                    복습 카드
                  </span>
                )}
                {!isPinned && (
                  <span className="inline-flex items-center rounded-full bg-[#F2F4F6] px-2 py-0.5 text-[10px] font-semibold text-[#6B7684]">
                    대화 기록
                  </span>
                )}
                <p className="truncate text-[14px] font-semibold text-[#101828]">
                  {session.title || '제목 없는 대화'}
                </p>
              </div>
              <p className="mt-1 text-[12px] text-[#6a7282]">
                {session.message_count || 0}개 메시지
                {session.last_message_at ? ` \u00B7 ${formatRelativeDate(session.last_message_at)}` : ''}
              </p>
              {isOpening && <p className="mt-1 text-[11px] text-[#99a1af]">불러오는 중...</p>}
            </button>

            <div className="flex gap-1.5">
              {isPinned && (
                <button
                  type="button"
                  onClick={() => openSession(session.id)}
                  className="rounded-lg border border-[#FFF2E8] bg-[#FFF2E8] px-2 py-1 text-[11px] font-medium text-[#FF6B00] transition-colors hover:bg-[#FFE4D0]"
                >
                  이어하기
                </button>
              )}
              <button
                type="button"
                onClick={() => removeSession(session.id)}
                className="rounded-lg border border-[#f3f4f6] px-2 py-1 text-[11px] text-[#6a7282] transition-colors hover:bg-[#fff2f0] hover:text-[#ef4444]"
                disabled={isDeleting}
              >
                {isDeleting ? '삭제 중' : '삭제'}
              </button>
            </div>
          </div>
        </div>

        {/* 핀 고정 세션 확장 시 ReviewCard 표시 */}
        {isPinned && isExpanded && (
          <div className="ml-2">
            <ReviewCard
              session={session}
              onResumeChat={handleResumeChat}
              onViewFull={handleViewFull}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#f9fafb] pb-[calc(var(--safe-bottom-offset,172px)+16px)]">
      <header className="sticky top-0 z-10 border-b border-[#f3f4f6] bg-white/95 backdrop-blur">
        <div className="container py-3.5">
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={handleBack}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-[#f3f4f6] text-[#6a7282] transition-colors hover:bg-[#eceef1]"
              aria-label="뒤로가기"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>

            <h1 className="truncate flex-1 text-center text-[17px] font-bold tracking-[-0.01em] text-[#101828]">대화 기록</h1>

            <button
              type="button"
              onClick={() => refreshSessions().catch(() => {})}
              className="rounded-lg border border-[#e5e7eb] bg-white px-2.5 py-1.5 text-[12px] font-semibold text-[#4a5565] transition-colors hover:bg-[#f9fafb]"
            >
              새로고침
            </button>
          </div>
        </div>
      </header>

      <main className="container py-4">
        {safeSessions.length === 0 ? (
          <div className="rounded-2xl border border-[#f3f4f6] bg-white px-4 py-6 text-center text-[14px] text-[#6a7282]">
            저장된 대화가 없습니다.
          </div>
        ) : (
          <div className="space-y-4">
            {/* 복습 카드 (핀 고정 세션) */}
            {pinnedSessions.length > 0 && (
              <div className="space-y-2">
                <p className="text-[13px] font-semibold text-[#8B95A1]">
                  고정된 복습 카드 ({pinnedSessions.length})
                </p>
                {pinnedSessions.map((session) => renderSessionRow(session, { isPinned: true }))}
              </div>
            )}

            {/* 일반 대화 기록 */}
            {regularSessions.length > 0 && (
              <div className="space-y-2">
                {pinnedSessions.length > 0 && (
                  <p className="text-[13px] font-semibold text-[#8B95A1]">
                    대화 기록 ({regularSessions.length})
                  </p>
                )}
                {regularSessions.map((session) => renderSessionRow(session, { isPinned: false }))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
