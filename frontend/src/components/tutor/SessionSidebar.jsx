/**
 * SessionSidebar - 세션 목록 UI
 */
import { formatRelativeDate } from '../../utils/dateFormat';

export default function SessionSidebar({
  sessions, activeSessionId, isOpen,
  onSessionClick, onDeleteSession,
}) {
  if (!isOpen) return null;
  const safeSessions = Array.isArray(sessions) ? sessions : [];

  return (
    <div className="border-t border-border bg-surface-elevated">
      {safeSessions.length === 0 ? (
        <div className="px-4 py-4 text-sm text-text-secondary">이전 대화가 없습니다.</div>
      ) : (
        <div className="max-h-48 overflow-y-auto">
          {safeSessions.map((session) => (
            <div
              key={session.id}
              onClick={() => onSessionClick(session.id)}
              className={`px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-surface transition-colors ${
                activeSessionId === session.id ? 'bg-primary/10 border-l-2 border-primary' : ''
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm text-text-primary truncate">{session.title || '제목 없음'}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-text-secondary">{session.message_count || 0}개 메시지</span>
                  {session.last_message_at && (
                    <span className="text-xs text-text-secondary">· {formatRelativeDate(session.last_message_at)}</span>
                  )}
                </div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id); }}
                className="ml-2 p-1.5 rounded hover:bg-error-light text-text-secondary hover:text-error transition-colors"
                title="삭제"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
