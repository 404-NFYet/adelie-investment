/**
 * SessionSidebar - 세션 목록 UI (접기/펼치기)
 */
import { formatRelativeDate } from '../../utils/dateFormat';

export default function SessionSidebar({
  sessions, activeSessionId, isOpen, onToggle,
  onSessionClick, onDeleteSession,
}) {
  if (!sessions || sessions.length === 0) return null;

  return (
    <div className="border-t border-border">
      <button
        onClick={onToggle}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-text-secondary hover:bg-surface transition-colors"
      >
        <span className="font-medium">대화 목록 ({sessions.length})</span>
        <span className={`transform transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {isOpen && (
        <div className="max-h-48 overflow-y-auto border-t border-border">
          {sessions.map((session) => (
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
