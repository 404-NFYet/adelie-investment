/**
 * Profile.jsx - 프로필/설정 화면
 * 사용자 정보, 난이도 설정, 테마 전환, 로그아웃
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUser, DIFFICULTY_LEVELS } from '../contexts';
import { useTheme } from '../contexts/ThemeContext';
import { motion } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';

const DIFFICULTY_OPTIONS = [
  { value: DIFFICULTY_LEVELS.BEGINNER, label: '입문' },
  { value: DIFFICULTY_LEVELS.ELEMENTARY, label: '초급' },
  { value: DIFFICULTY_LEVELS.INTERMEDIATE, label: '중급' },
];

export default function Profile() {
  const navigate = useNavigate();
  const { user, settings, setDifficulty, logout } = useUser();
  const { isDarkMode, toggleTheme } = useTheme();

  const isLoggedIn = user?.isAuthenticated;
  const isGuest = user?.isGuest;

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader />

      <main className="container py-6 space-y-6">
        {/* 사용자 정보 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="card"
        >
          <h2 className="text-lg font-bold mb-3">프로필</h2>
          {isLoggedIn ? (
            <div className="space-y-1">
              {user.username && (
                <p className="text-text-primary font-medium">{user.username}</p>
              )}
              {user.email && (
                <p className="text-text-secondary text-sm">{user.email}</p>
              )}
            </div>
          ) : (
            <p className="text-text-secondary text-sm">게스트 모드</p>
          )}
        </motion.div>

        {/* 난이도 설정 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="card"
        >
          <h2 className="text-lg font-bold mb-3">학습 난이도</h2>
          <div className="flex gap-2">
            {DIFFICULTY_OPTIONS.map((option) => {
              const isSelected = settings.difficulty === option.value;
              return (
                <button
                  key={option.value}
                  onClick={() => setDifficulty(option.value)}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isSelected
                      ? 'bg-primary text-white'
                      : 'bg-surface border border-border text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
        </motion.div>

        {/* 테마 설정 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="card"
        >
          <h2 className="text-lg font-bold mb-3">테마</h2>
          <button
            onClick={toggleTheme}
            className="w-full flex items-center justify-between py-2"
          >
            <span className="text-text-primary text-sm">
              {isDarkMode ? '다크 모드' : '라이트 모드'}
            </span>
            <div
              className={`w-12 h-6 rounded-full relative transition-colors ${
                isDarkMode ? 'bg-primary' : 'bg-border'
              }`}
            >
              <div
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${
                  isDarkMode ? 'translate-x-6' : 'translate-x-0.5'
                }`}
              />
            </div>
          </button>
        </motion.div>

        {/* 계정 관련 버튼 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="space-y-3"
        >
          {isLoggedIn ? (
            <button
              onClick={() => {
                logout();
                navigate('/auth');
              }}
              className="btn-secondary w-full"
            >
              로그아웃
            </button>
          ) : (
            <button
              onClick={() => navigate('/auth')}
              className="btn-primary w-full"
            >
              계정 등록하기
            </button>
          )}
        </motion.div>

        {/* 앱 정보 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.4 }}
          className="text-center pt-4"
        >
          <p className="text-text-secondary text-xs">Narrative Investment v0.1.0</p>
        </motion.div>
      </main>
    </div>
  );
}
