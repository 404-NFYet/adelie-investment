import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../../contexts/UserContext';
import { notificationApi } from '../../api';

export default function AppHeader({ showBack = false, title = null }) {
  const navigate = useNavigate();
  const { user } = useUser();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user?.id) return;
    notificationApi.getUnreadCount()
      .then(data => setUnreadCount(data.unread_count || 0))
      .catch(() => {});
  }, [user?.id]);

  return (
    <header className="sticky top-0 bg-surface-elevated/80 backdrop-blur-md border-b border-border z-10">
      <div className="container py-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {showBack && (
              <button onClick={() => navigate(-1)} className="p-1 -ml-1 text-text-secondary hover:text-text-primary transition-colors">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M15 18l-6-6 6-6" />
                </svg>
              </button>
            )}
            <div
              className="flex items-center gap-1.5 cursor-pointer"
              onClick={() => navigate('/')}
            >
              <img src="/images/penguin-3d.png" alt="Adelie" className="w-7 h-7" />
              <h1 className="text-lg font-bold tracking-tight text-text-primary">
                ADELIE
              </h1>
            </div>
            {title && (
              <span className="text-sm text-text-secondary ml-1">/ {title}</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {/* 알림 */}
            <button
              onClick={() => navigate('/notifications')}
              className="relative w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-surface transition-colors"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              {unreadCount > 0 && (
                <span className="absolute top-0.5 right-0.5 w-4 h-4 bg-error text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
            {/* 프로필 */}
            <button
              onClick={() => navigate('/profile')}
              className="w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-surface transition-colors"
              aria-label="프로필"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
