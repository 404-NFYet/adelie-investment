import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';
import { useUser } from '../../contexts/UserContext';
import { notificationApi } from '../../api';

export default function AppHeader({ showBack = false, title = null }) {
  const navigate = useNavigate();
  const { isDarkMode, toggleTheme } = useTheme();
  const { user } = useUser();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user?.id) return;
    notificationApi.getUnreadCount(user.id)
      .then(data => setUnreadCount(data.unread_count || 0))
      .catch(() => {});
  }, [user?.id]);

  return (
    <header className="sticky top-0 bg-surface-elevated shadow-card z-10">
      <div className="container py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {showBack && (
              <button onClick={() => navigate(-1)} className="p-1 -ml-1 text-text-secondary hover:text-text-primary">
                <span className="text-lg">←</span>
              </button>
            )}
            <div
              className="flex items-center gap-1.5 cursor-pointer"
              onClick={() => navigate('/')}
            >
              <span className="text-xl">🐧</span>
              <h1 className="font-cursive text-2xl text-primary">
                아델리에 투자
              </h1>
            </div>
            {title && (
              <span className="text-sm text-text-secondary ml-1">/ {title}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/notifications')}
              className="relative w-8 h-8 rounded-full bg-surface flex items-center justify-center border border-border text-sm"
            >
              🔔
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
            <button
              onClick={toggleTheme}
              className="w-8 h-8 rounded-full bg-surface flex items-center justify-center border border-border text-sm"
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
