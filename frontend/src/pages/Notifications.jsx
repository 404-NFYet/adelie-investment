/**
 * Notifications.jsx - 알림 페이지
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';
import { useUser } from '../contexts/UserContext';
import { notificationApi } from '../api';

const NotifIcon = ({ type }) => {
  const icons = {
    reward: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
    dwell: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
      </svg>
    ),
    bonus: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="20 12 20 22 4 22 4 12" /><rect x="2" y="7" width="20" height="5" /><line x1="12" y1="22" x2="12" y2="7" /><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z" /><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z" />
      </svg>
    ),
    system: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
    ),
  };
  return icons[type] || icons.system;
};

const TYPE_LABELS = {
  reward: '보상',
  dwell: '체류 보상',
  bonus: '보너스',
  system: '시스템',
};

function NotificationItem({ notification, onRead, onDelete }) {
  const label = TYPE_LABELS[notification.type] || TYPE_LABELS.system;
  const isUnread = !notification.is_read;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card flex items-start gap-3 relative ${isUnread ? '' : 'opacity-75'}`}
      onClick={() => isUnread && onRead?.(notification.id)}
    >
      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-primary">
        <NotifIcon type={notification.type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-0.5 rounded">
            {label}
          </span>
          {isUnread && (
            <span className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
          )}
        </div>
        <h3 className="font-semibold text-sm">{notification.title}</h3>
        <p className="text-xs text-text-secondary mt-0.5">{notification.message}</p>
        <p className="text-xs text-text-muted mt-1">
          {new Date(notification.created_at).toLocaleDateString('ko-KR', {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
          })}
        </p>
      </div>
      {/* 삭제 버튼 */}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete?.(notification.id); }}
        className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-full hover:bg-border-light text-text-muted hover:text-text-secondary transition-colors"
        aria-label="삭제"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </motion.div>
  );
}

export default function Notifications() {
  const { user } = useUser();
  const userId = user?.id;

  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!userId) return;
    setIsLoading(true);
    notificationApi.getAll(1, 50)
      .then(data => {
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [userId]);

  const handleRead = async (notificationId) => {
    try {
      await notificationApi.markAsRead([notificationId]);
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {}
  };

  const handleReadAll = async () => {
    if (unreadCount === 0) return;
    try {
      await notificationApi.markAsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {}
  };

  const handleDelete = async (notificationId) => {
    try {
      await notificationApi.deleteOne(notificationId);
      const deleted = notifications.find(n => n.id === notificationId);
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
      if (deleted && !deleted.is_read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    } catch {}
  };

  const handleDeleteRead = async () => {
    try {
      await notificationApi.deleteRead();
      setNotifications(prev => prev.filter(n => !n.is_read));
    } catch {}
  };

  const hasReadNotifs = notifications.some(n => n.is_read);

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader showBack title="알림" />

      <main className="container py-6 space-y-4">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">
            알림 {unreadCount > 0 && <span className="text-primary text-sm ml-1">({unreadCount})</span>}
          </h2>
          <div className="flex items-center gap-3">
            {hasReadNotifs && (
              <button
                onClick={handleDeleteRead}
                className="text-xs text-red-400 font-medium"
              >
                읽은 알림 삭제
              </button>
            )}
            {unreadCount > 0 && (
              <button
                onClick={handleReadAll}
                className="text-xs text-primary font-medium"
              >
                모두 읽음
              </button>
            )}
          </div>
        </div>

        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="animate-pulse text-text-secondary text-sm">로딩 중...</div>
          </div>
        )}

        {!isLoading && notifications.length === 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-12">
            <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
            </div>
            <p className="text-text-secondary text-sm">아직 알림이 없습니다</p>
            <p className="text-text-muted text-xs mt-1">브리핑을 완독하면 보상 알림을 받을 수 있어요</p>
          </motion.div>
        )}

        {!isLoading && notifications.length > 0 && (
          <div className="space-y-3">
            {notifications.map(n => (
              <NotificationItem key={n.id} notification={n} onRead={handleRead} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
