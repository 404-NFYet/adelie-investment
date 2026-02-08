import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/auth';

const UserContext = createContext(null);

// Difficulty levels
export const DIFFICULTY_LEVELS = {
  BEGINNER: 'beginner',      // 입문
  ELEMENTARY: 'elementary',  // 초급
  INTERMEDIATE: 'intermediate', // 중급
};

const DEFAULT_USER_SETTINGS = {
  difficulty: DIFFICULTY_LEVELS.BEGINNER,
  hasCompletedOnboarding: false,
  bookmarks: [],
  history: [],
};

export function UserProvider({ children }) {
  const [user, setUser] = useState(null);
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('userSettings');
    if (saved) {
      try {
        return { ...DEFAULT_USER_SETTINGS, ...JSON.parse(saved) };
      } catch {
        return DEFAULT_USER_SETTINGS;
      }
    }
    return DEFAULT_USER_SETTINGS;
  });
  const [isLoading, setIsLoading] = useState(true);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('userSettings', JSON.stringify(settings));
  }, [settings]);

  // Initialize user (check for token and restore user info)
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      authApi.getMe(token)
        .then(data => {
          setUser({
            id: data.id,
            email: data.email,
            username: data.username,
            isAuthenticated: true,
          });
        })
        .catch(() => {
          // 토큰 만료 또는 유효하지 않음 → 제거
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const updateSettings = (newSettings) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
  };

  const setDifficulty = (difficulty) => {
    setSettings((prev) => ({ ...prev, difficulty }));
  };

  const completeOnboarding = () => {
    setSettings((prev) => ({ ...prev, hasCompletedOnboarding: true }));
  };

  const addBookmark = (item) => {
    setSettings((prev) => ({
      ...prev,
      bookmarks: [...prev.bookmarks.filter((b) => b.id !== item.id), item],
    }));
  };

  const removeBookmark = (itemId) => {
    setSettings((prev) => ({
      ...prev,
      bookmarks: prev.bookmarks.filter((b) => b.id !== itemId),
    }));
  };

  const addToHistory = (item) => {
    setSettings((prev) => ({
      ...prev,
      history: [
        item,
        ...prev.history.filter((h) => h.id !== item.id).slice(0, 49),
      ],
    }));
  };

  const login = (authResponse) => {
    setUser({
      id: authResponse.user?.id,
      email: authResponse.user?.email,
      username: authResponse.user?.username,
      isAuthenticated: true,
    });
    localStorage.setItem('token', authResponse.accessToken);
    if (authResponse.refreshToken) {
      localStorage.setItem('refreshToken', authResponse.refreshToken);
    }
  };

  const loginAsGuest = () => {
    setUser({ isAuthenticated: false, isGuest: true });
    setSettings(prev => ({ ...prev, hasCompletedOnboarding: true }));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
  };

  return (
    <UserContext.Provider
      value={{
        user,
        settings,
        isLoading,
        updateSettings,
        setDifficulty,
        completeOnboarding,
        addBookmark,
        removeBookmark,
        addToHistory,
        login,
        loginAsGuest,
        logout,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
