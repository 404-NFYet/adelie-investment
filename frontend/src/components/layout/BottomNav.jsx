import { useNavigate, useLocation } from 'react-router-dom';

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  // Don't show on learning flow pages or auth/onboarding
  const hiddenPaths = ['/matching', '/story', '/comparison', '/companies', '/auth', '/onboarding', '/narrative'];
  if (hiddenPaths.some(p => location.pathname.startsWith(p))) return null;

  const tabs = [
    { id: 'home', label: '홈', path: '/', onClick: () => navigate('/') },
    { id: 'search', label: '검색', path: '/search', onClick: () => navigate('/search') },
    { id: 'portfolio', label: '투자', path: '/portfolio', onClick: () => navigate('/portfolio') },
    { id: 'tutor', label: 'AI 튜터', path: '/tutor', onClick: () => navigate('/tutor') },
    { id: 'profile', label: '마이', path: '/profile', onClick: () => navigate('/profile') },
  ];

  const icons = {
    home: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
    search: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
    portfolio: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
    tutor: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    profile: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
      </svg>
    ),
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-surface-elevated/80 backdrop-blur-md border-t border-border py-2 z-20 max-w-mobile mx-auto">
      <div className="flex justify-around">
        {tabs.map(tab => {
          const isActive = tab.path && location.pathname === tab.path;
          return (
            <button
              key={tab.id}
              onClick={tab.onClick}
              className={`flex flex-col items-center gap-0.5 py-1 px-3 transition-colors ${isActive ? 'text-primary' : 'text-text-secondary'}`}
            >
              {icons[tab.id]}
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
