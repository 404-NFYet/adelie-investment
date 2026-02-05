import { useNavigate, useLocation } from 'react-router-dom';
import { useTutor } from '../contexts';

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { openTutor } = useTutor();
  
  // Don't show on learning flow pages or auth/onboarding
  const hiddenPaths = ['/matching', '/story', '/comparison', '/companies', '/auth', '/onboarding'];
  if (hiddenPaths.some(p => location.pathname.startsWith(p))) return null;

  const tabs = [
    { id: 'home', icon: '🏠', label: '홈', path: '/', onClick: () => navigate('/') },
    { id: 'search', icon: '🔍', label: '검색', path: '/search', onClick: () => navigate('/search') },
    { id: 'tutor', icon: '💬', label: 'AI 튜터', path: null, onClick: () => openTutor() },
    { id: 'profile', icon: '👤', label: '마이', path: '/profile', onClick: () => navigate('/profile') },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-surface-elevated border-t border-border py-2 z-20 max-w-mobile mx-auto">
      <div className="flex justify-around">
        {tabs.map(tab => {
          const isActive = tab.path && location.pathname === tab.path;
          return (
            <button
              key={tab.id}
              onClick={tab.onClick}
              className={`flex flex-col items-center gap-0.5 py-1 px-3 ${isActive ? 'text-primary' : 'text-text-secondary'}`}
            >
              <span className="text-lg">{tab.icon}</span>
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
