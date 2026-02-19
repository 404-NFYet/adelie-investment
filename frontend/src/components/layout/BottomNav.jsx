import { useNavigate, useLocation } from 'react-router-dom';

const HIDDEN_PREFIXES = [
  '/landing',
  '/auth',
  '/onboarding',
  '/story',
  '/comparison',
  '/companies',
  '/case',
  '/notifications',
  '/tutor',
];
const HIDDEN_EXACT = ['/'];

const tabs = [
  { id: 'education', label: '교육', path: '/education' },
  { id: 'home', label: '홈', path: '/home' },
  { id: 'portfolio', label: '모의투자', path: '/portfolio' },
];

const icons = {
  education: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 6l10-4 10 4-10 4L2 6z" />
      <path d="M6 10v5c0 1.7 2.7 3 6 3s6-1.3 6-3v-5" />
    </svg>
  ),
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
};

function isActivePath(tabPath, pathname) {
  if (tabPath === '/home' || tabPath === '/education') {
    return pathname === tabPath;
  }
  return pathname === tabPath || pathname.startsWith(`${tabPath}/`);
}

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  if (
    HIDDEN_EXACT.includes(location.pathname) ||
    HIDDEN_PREFIXES.some((prefix) => location.pathname.startsWith(prefix))
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
              {icons[tab.id]}
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
