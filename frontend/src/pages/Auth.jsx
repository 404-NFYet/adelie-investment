import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { authApi } from '../api';
import { useUser } from '../contexts';

const TABS = {
  LOGIN: 'login',
  REGISTER: 'register',
};

const EMAIL_DOMAINS = [
  { label: 'gmail.com', value: 'gmail.com' },
  { label: 'naver.com', value: 'naver.com' },
  { label: 'daum.net', value: 'daum.net' },
  { label: 'kakao.com', value: 'kakao.com' },
  { label: '직접입력', value: '' },
];

/* SVG Eye 아이콘 */
function EyeIcon({ open }) {
  if (open) {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

export default function Auth() {
  const [activeTab, setActiveTab] = useState(TABS.LOGIN);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, settings, setDifficulty } = useUser();
  const [selectedDifficulty, setSelectedDifficulty] = useState(settings.difficulty || 'beginner');
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  // 회원가입 이메일 분리 상태
  const [emailLocal, setEmailLocal] = useState('');
  const [emailDomain, setEmailDomain] = useState('gmail.com');
  const [customDomain, setCustomDomain] = useState('');

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setUsername('');
    setError('');
    setEmailLocal('');
    setEmailDomain('gmail.com');
    setCustomDomain('');
  };

  const handleTabSwitch = (tab) => {
    setActiveTab(tab);
    resetForm();
  };

  // 회원가입 이메일 조합
  const getRegisterEmail = () => {
    const domain = emailDomain || customDomain;
    return domain ? `${emailLocal}@${domain}` : emailLocal;
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await authApi.login(email, password);
      login(response);
      navigate('/home');
    } catch (err) {
      setError(err.message || '로그인에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) { setError('비밀번호는 8자 이상이어야 합니다'); return; }
    if (!username || username.length < 2 || username.length > 10) { setError('사용자명은 2~10자로 입력해주세요'); return; }
    const registerEmail = getRegisterEmail();
    if (!registerEmail.includes('@') || !registerEmail.split('@')[1]) {
      setError('올바른 이메일 형식이 아닙니다');
      return;
    }
    setLoading(true);
    try {
      const response = await authApi.register(registerEmail, password, username);
      login(response);
      setDifficulty(selectedDifficulty);
      navigate('/home');
    } catch (err) {
      setError(err.message || '회원가입에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-mobile">
        {/* Logo */}
        <motion.div
          className="text-center mb-8 cursor-pointer"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={() => navigate('/')}
        >
          <h1 className="font-handwriting text-4xl text-primary">아델리에</h1>
          <p className="text-text-secondary text-sm mt-1">역사는 반복된다</p>
        </motion.div>

        {/* Card */}
        <motion.div
          className="card p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {/* Tab Switcher */}
          <div className="flex rounded-xl bg-surface mb-6 p-1">
            <button
              onClick={() => handleTabSwitch(TABS.LOGIN)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === TABS.LOGIN
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              로그인
            </button>
            <button
              onClick={() => handleTabSwitch(TABS.REGISTER)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === TABS.REGISTER
                  ? 'bg-primary text-white shadow-sm'
                  : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              회원가입
            </button>
          </div>

          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Forms */}
          <AnimatePresence mode="wait">
            {activeTab === TABS.LOGIN ? (
              <motion.form
                key="login"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
                onSubmit={handleLogin}
                className="space-y-4"
              >
                <div>
                  <label htmlFor="login-email" className="block text-sm text-text-secondary mb-1.5">이메일</label>
                  <input
                    id="login-email"
                    name="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="input w-full"
                    required
                  />
                </div>
                <div>
                  <label htmlFor="login-password" className="block text-sm text-text-secondary mb-1.5">비밀번호</label>
                  <div className="relative">
                    <input
                      id="login-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="input w-full pr-10"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                    >
                      <EyeIcon open={showPassword} />
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-3 rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '로그인 중...' : '로그인'}
                </button>
              </motion.form>
            ) : (
              <motion.form
                key="register"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                onSubmit={handleRegister}
                className="space-y-4"
              >
                {/* 이메일 (로컬파트 + 도메인 선택) */}
                <div>
                  <label htmlFor="reg-email-local" className="block text-sm text-text-secondary mb-1.5">이메일</label>
                  <div className="flex gap-1 items-center">
                    <input
                      id="reg-email-local"
                      name="emailLocal"
                      type="text"
                      value={emailLocal}
                      onChange={(e) => setEmailLocal(e.target.value)}
                      placeholder="아이디"
                      className="input flex-1 min-w-0"
                      required
                    />
                    <span className="text-text-secondary text-sm flex-shrink-0">@</span>
                    {emailDomain ? (
                      <select
                        id="reg-email-domain"
                        name="emailDomain"
                        value={emailDomain}
                        onChange={(e) => setEmailDomain(e.target.value)}
                        className="input flex-1 min-w-0 text-sm"
                        aria-label="이메일 도메인"
                      >
                        {EMAIL_DOMAINS.map(d => (
                          <option key={d.value} value={d.value}>{d.label}</option>
                        ))}
                      </select>
                    ) : (
                      <div className="flex-1 min-w-0 flex gap-1">
                        <input
                          id="reg-custom-domain"
                          name="customDomain"
                          type="text"
                          value={customDomain}
                          onChange={(e) => setCustomDomain(e.target.value)}
                          placeholder="도메인"
                          className="input flex-1 min-w-0 text-sm"
                          aria-label="직접 입력 도메인"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => { setEmailDomain('gmail.com'); setCustomDomain(''); }}
                          className="text-xs text-primary flex-shrink-0 px-1"
                        >
                          목록
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* 비밀번호 */}
                <div>
                  <label htmlFor="reg-password" className="block text-sm text-text-secondary mb-1.5">비밀번호</label>
                  <div className="relative">
                    <input
                      id="reg-password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="input w-full pr-10"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary"
                    >
                      <EyeIcon open={showPassword} />
                    </button>
                  </div>
                  <p className="text-xs text-text-muted mt-1">8자 이상, 영문+숫자 조합 권장</p>
                </div>

                {/* 사용자 이름 */}
                <div>
                  <label htmlFor="reg-username" className="block text-sm text-text-secondary mb-1.5">사용자 이름</label>
                  <input
                    id="reg-username"
                    name="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="홍길동"
                    className="input w-full"
                    maxLength={10}
                    required
                  />
                  <p className="text-xs text-text-muted mt-1">2~10자</p>
                </div>

                {/* 투자 경험 수준 */}
                <div>
                  <label className="block text-sm text-text-secondary mb-1.5">투자 경험 수준</label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { value: 'beginner', label: '입문' },
                      { value: 'elementary', label: '초급' },
                      { value: 'intermediate', label: '중급' },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setSelectedDifficulty(opt.value)}
                        className={`py-2 rounded-lg text-sm font-medium transition-all ${
                          selectedDifficulty === opt.value
                            ? 'bg-primary text-white'
                            : 'bg-surface text-text-secondary border border-border'
                        }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary w-full py-3 rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '가입 중...' : '회원가입'}
                </button>
              </motion.form>
            )}
          </AnimatePresence>
        </motion.div>

      </div>
    </div>
  );
}
