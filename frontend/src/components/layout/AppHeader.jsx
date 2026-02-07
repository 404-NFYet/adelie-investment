import { useNavigate } from 'react-router-dom';
import { useTheme } from '../../contexts/ThemeContext';

export default function AppHeader({ showBack = false, title = null }) {
  const navigate = useNavigate();
  const { isDarkMode, toggleTheme } = useTheme();

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
            <h1 
              className="font-cursive text-2xl text-primary cursor-pointer" 
              onClick={() => navigate('/')}
            >
              History Mirror
            </h1>
            {title && (
              <span className="text-sm text-text-secondary ml-1">/ {title}</span>
            )}
          </div>
          <button
            onClick={toggleTheme}
            className="w-8 h-8 rounded-full bg-surface flex items-center justify-center border border-border text-sm"
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </div>
    </header>
  );
}
