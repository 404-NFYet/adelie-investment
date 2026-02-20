import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../../contexts/UserContext';
import { notificationApi } from '../../api';

function formatName(rawName) {
  if (!rawName) return '펭귄님';
  return rawName.endsWith('님') ? rawName : `${rawName}님`;
}

export default function DashboardHeader({ subtitle = '오늘도 성장을 위한 첫걸음 🐧' }) {
  const navigate = useNavigate();
  const { user } = useUser();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!user?.id) return;
    notificationApi.getUnreadCount()
      .then((data) => setUnreadCount(data.unread_count || 0))
      .catch(() => {});
  }, [user?.id]);

  const greeting = useMemo(() => {
    const preferredName = user?.username || user?.email?.split('@')?.[0];
    return `안녕하세요, ${formatName(preferredName)}!`;
  }, [user?.email, user?.username]);

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background">
      <div className="container py-3.5">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/home')}
              className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border bg-white shadow-sm transition hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              aria-label="홈으로 이동"
            >
              <img
                src="/images/penguin-3d.png"
                alt="프로필"
                className="h-8 w-8 object-contain"
              />
            </button>
            <div className="min-w-0">
              <p className="truncate text-[clamp(1.1rem,4.6vw,1.25rem)] font-bold leading-tight tracking-[-0.02em] text-[#101828]">
                {greeting}
              </p>
              <p className="truncate text-xs text-[#6a7282]">{subtitle}</p>
            </div>
          </div>

          <div className="ml-3 flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate('/notifications')}
              className="relative flex h-10 w-10 items-center justify-center rounded-2xl border border-border bg-white text-text-secondary shadow-sm transition hover:text-text-primary"
              aria-label="알림"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.73 21a2 2 0 0 1-3.46 0" />
              </svg>
              {unreadCount > 0 && (
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-primary" />
              )}
            </button>

            <button
              type="button"
              onClick={() => navigate('/profile')}
              className="flex h-10 w-10 items-center justify-center rounded-2xl border border-border bg-white text-text-secondary shadow-sm transition hover:text-text-primary"
              aria-label="프로필"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
