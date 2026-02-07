/**
 * Notifications.jsx - 알림 페이지
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';
import { useUser } from '../contexts/UserContext';
import { notificationApi } from '../api';

const TYPE_CONFIG = {
  reward: { icon: '💰', label: '보상' },
  dwell: { icon: '⏱️', label: '체류 보상' },
  bonus: { icon: '🎁', label: '보너스' },
  system: { icon: '📢', label: '시스템' },
};

function NotificationItem({ notification, onRead }) {
  const config = TYPE_CONFIG[notification.type] || TYPE_CONFIG.system;
  const isUnread = !notification.is_read;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card flex items-start gap-3 ${isUnread ? 'border-l-4 border-l-primary' : 'opacity-75'}`}
      onClick={() => isUnread && onRead?.(notification.id)}
    >
      <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
        <span className="text-lg">{config.icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-0.5 rounded">
            {config.label}
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
    notificationApi.getAll(userId, 1, 50)
      .then(data => {
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [userId]);

  const handleRead = async (notificationId) => {
    try {
      await notificationApi.markAsRead(userId, [notificationId]);
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, is_read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch {}
  };

  const handleReadAll = async () => {
    if (unreadCount === 0) return;
    try {
      await notificationApi.markAsRead(userId);
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {}
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader showBack title="알림" />

      <main className="container py-6 space-y-4">
        {/* 헤더 */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">
            알림 {unreadCount > 0 && <span className="text-primary text-sm ml-1">({unreadCount})</span>}
          </h2>
          {unreadCount > 0 && (
            <button
              onClick={handleReadAll}
              className="text-xs text-primary font-medium"
            >
              모두 읽음
            </button>
          )}
        </div>

        {isLoading && (
          <div className="flex justify-center py-12">
            <div className="animate-pulse text-text-secondary text-sm">로딩 중...</div>
          </div>
        )}

        {!isLoading && notifications.length === 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-12">
            <p className="text-3xl mb-3">🔔</p>
            <p className="text-text-secondary text-sm">아직 알림이 없습니다</p>
            <p className="text-text-muted text-xs mt-1">브리핑을 완독하면 보상 알림을 받을 수 있어요</p>
          </motion.div>
        )}

        {!isLoading && notifications.length > 0 && (
          <div className="space-y-3">
            {notifications.map(n => (
              <NotificationItem key={n.id} notification={n} onRead={handleRead} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
