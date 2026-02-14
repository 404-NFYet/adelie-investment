import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

const HIDDEN_PREFIXES = [
  '/landing',
  '/auth',
  '/onboarding',
  '/story',
  '/comparison',
  '/companies',
  '/case',
  '/notifications',
];
const HIDDEN_EXACT = ['/'];

const tabs = [
  { id: 'home', label: '홈', path: '/home' },
  { id: 'portfolio', label: '모의투자', path: '/portfolio' },
  { id: 'tutor', label: 'AI 튜터', path: '/tutor' },
  { id: 'profile', label: '프로필', path: '/profile' },
];

const icons = {
  home: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  portfolio: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 18l6-6 4 4 6-8" />
      <path d="M18 8h2v2" />
    </svg>
  ),
  tutor: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  profile: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  ),
};

function isActivePath(tabPath, pathname) {
  if (tabPath === '/home') {
    return pathname === '/home';
  }
  return pathname === tabPath || pathname.startsWith(`${tabPath}/`);
}

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  if (
    HIDDEN_EXACT.includes(location.pathname) ||
    HIDDEN_PREFIXES.some(prefix => location.pathname.startsWith(prefix))
  ) {
    return null;
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 max-w-mobile mx-auto bg-surface-elevated border-t border-border py-2">
      <div className="flex justify-around">
        {tabs.map((tab) => {
          const isActive = isActivePath(tab.path, location.pathname);

          return (
            <button
              key={tab.id}
              onClick={() => navigate(tab.path)}
              className={`relative flex flex-col items-center gap-0.5 py-1 px-2 transition-colors ${
                isActive ? 'text-primary' : 'text-[#364153]'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute -top-2 left-1/2 -translate-x-1/2 w-5 h-0.5 rounded-full bg-primary"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              {icons[tab.id]}
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
