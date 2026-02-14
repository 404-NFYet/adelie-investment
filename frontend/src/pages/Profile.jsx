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

/* ── 문의사항 컴포넌트 ── */
function ContactSection() {
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!message.trim()) return;
    setSubmitting(true);
    try {
      await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ page: 'contact', rating: null, comment: message }),
      });
      setSubmitted(true);
    } catch {}
    setSubmitting(false);
  };

  if (submitted) {
    return (
      <div className="text-center py-4">
        <img src="/images/penguin-3d.png" alt="Adelie" className="w-10 h-10 mx-auto mb-1" />
        <p className="text-sm font-medium">문의가 접수되었습니다!</p>
        <p className="text-xs text-text-secondary mt-1">빠른 시일 내에 답변드리겠습니다.</p>
      </div>
    );
  }

  return (
    <>
      <h2 className="text-lg font-bold mb-3">문의사항</h2>
      <p className="text-sm text-text-secondary mb-4">
        서비스 이용 중 궁금한 점이나 개선 사항이 있으시면 아래에 남겨주세요.
      </p>
      <textarea
        id="inquiry-message"
        name="message"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="문의 내용을 입력해주세요"
        aria-label="문의 내용"
        className="w-full p-3 rounded-xl border border-border bg-surface text-sm resize-none mb-3"
        rows={3}
      />
      <button
        onClick={handleSubmit}
        disabled={!message.trim() || submitting}
        className="w-full py-2.5 rounded-xl font-semibold text-white bg-primary hover:bg-primary/90 disabled:opacity-40 transition-colors text-sm"
      >
        {submitting ? '전송 중...' : '보내기'}
      </button>
    </>
  );
}

const DIFFICULTY_OPTIONS = [
  { value: DIFFICULTY_LEVELS.BEGINNER, label: '입문' },
  { value: DIFFICULTY_LEVELS.ELEMENTARY, label: '초급' },
  { value: DIFFICULTY_LEVELS.INTERMEDIATE, label: '중급' },
];

export default function Profile() {
  const navigate = useNavigate();
  const { user, settings, setDifficulty, logout } = useUser();
  const { isDarkMode, toggleTheme } = useTheme();

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
          <div className="space-y-1">
            {user?.username && (
              <p className="text-text-primary font-medium">{user.username}</p>
            )}
            {user?.email && (
              <p className="text-text-secondary text-sm">{user.email}</p>
            )}
          </div>
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

        {/* 로그아웃 버튼 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="space-y-3"
        >
          <button
            onClick={() => {
              logout();
              navigate('/auth');
            }}
            className="btn-secondary w-full"
          >
            로그아웃
          </button>
        </motion.div>

        {/* 문의사항 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.35 }}
          className="card"
        >
          <ContactSection />
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
