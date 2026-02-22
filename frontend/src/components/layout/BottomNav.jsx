import { useNavigate, useLocation } from 'react-router-dom';
import useKeyboardInset from '../../hooks/useKeyboardInset';

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
  { id: 'portfolio', label: '투자', path: '/portfolio' },
  { id: 'home', label: '홈', path: '/home' },
  { id: 'education', label: '교육', path: '/education' },
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
  education: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="m22 10-10-5-10 5 10 5 10-5z" />
      <path d="M6 12v5c0 1.1 2.7 2 6 2s6-.9 6-2v-5" />
    </svg>
  ),
};

function isActivePath(tabPath, pathname, stateMode) {
  if (tabPath === '/portfolio') {
    if (pathname.startsWith('/agent')) return stateMode === 'stock';
    return pathname === tabPath || pathname.startsWith('/portfolio/');
  }

  if (tabPath === '/home') {
    if (pathname.startsWith('/agent')) return stateMode !== 'stock';
    return pathname === tabPath;
  }

  return pathname === tabPath || pathname.startsWith('/education/');
}

export default function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { keyboardOpen, inputFocused } = useKeyboardInset();

  if (
    HIDDEN_EXACT.includes(location.pathname) ||
    HIDDEN_PREFIXES.some((prefix) => location.pathname.startsWith(prefix)) ||
    keyboardOpen ||
    inputFocused
  ) {
    return null;
  }

  const stateMode = location.pathname.startsWith('/agent') ? (location.state?.mode || 'home') : null;

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-20 mx-auto h-[var(--bottom-nav-h,68px)] max-w-mobile border-t border-border bg-surface-elevated py-2">
      <div className="flex justify-around">
        {tabs.map((tab) => {
          const isActive = isActivePath(tab.path, location.pathname, stateMode);

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
