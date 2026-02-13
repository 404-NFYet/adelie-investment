/**
 * TutorChat.jsx - AI 튜터 대화 내역 페이지
 * 임시 비활성화 상태 — 준비 중 안내
 */
import AppHeader from '../components/layout/AppHeader';

export default function TutorChat() {
  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader title="AI 튜터" />

      <div className="max-w-mobile mx-auto px-4 pt-4 flex flex-col items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <h2 className="text-lg font-bold text-text-primary mb-2">AI 튜터 준비 중</h2>
        <p className="text-sm text-text-secondary text-center leading-relaxed">
          더 나은 학습 경험을 위해 준비하고 있어요.<br />
          빠르게 준비 될 예정이에요!
        </p>
      </div>
    </div>
  );
}
