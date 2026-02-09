/**
 * Home.jsx - 시나리오 카드 메인 화면 (adelie_fe_test 스타일)
 * 최대 5개의 시나리오 카드 표시
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import AppHeader from '../components/layout/AppHeader';
import NarrativeView from '../components/domain/NarrativeView';
import { getLatestBriefing } from '../api/briefings';

// 시나리오 카드 색상
const CARD_COLORS = [
  { bg: 'bg-orange-50', text: 'text-primary', border: 'border-orange-100' },
  { bg: 'bg-blue-50', text: 'text-blue-500', border: 'border-blue-100' },
  { bg: 'bg-purple-50', text: 'text-purple-600', border: 'border-purple-100' },
  { bg: 'bg-green-50', text: 'text-green-600', border: 'border-green-100' },
  { bg: 'bg-pink-50', text: 'text-pink-600', border: 'border-pink-100' },
];

export default function Home() {
  const navigate = useNavigate();
  const [briefing, setBriefing] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBriefing = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await getLatestBriefing();
        setBriefing(data);
      } catch (err) {
        console.error('브리핑 로딩 실패:', err);
        setError('브리핑을 불러오는데 실패했습니다.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchBriefing();
  }, []);

  // 로딩 상태
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background text-text-primary">
        <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-xs font-bold tracking-widest animate-pulse text-primary">오늘의 시장을 분석하고 있어요...</p>
      </div>
    );
  }

  // 에러 또는 데이터 없음
  if (error || !briefing || !briefing.scenarios || briefing.scenarios.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background text-text-primary p-6 text-center">
        <div className="mb-6 opacity-20">
          <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
          </svg>
        </div>
        <h1 className="text-2xl font-black mb-2 tracking-tight">아직 오늘의 브리핑이 없어요</h1>
        <p className="text-text-muted mb-4 text-sm">매일 아침 아델리가 자동으로 브리핑을 준비해요.</p>
        <p className="text-xs text-text-muted">조금만 기다려주세요!</p>
      </div>
    );
  }

  const scenarioCount = Math.min(briefing.scenarios.length, 5);

  // 시나리오 선택 시 내러티브 뷰 표시
  if (selectedScenario) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="h-screen w-full"
      >
        <NarrativeView
          briefing={briefing}
          scenario={selectedScenario}
          onBack={() => setSelectedScenario(null)}
        />
      </motion.div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader />

      <main className="w-full max-w-lg mx-auto p-5 pt-2">
        <AnimatePresence mode="wait">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            {/* Badge Header */}
            <div className="mb-8 text-center">
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-card mb-4"
              >
                <span className="text-[13px]">🐧</span>
                <span className="text-[10px] font-bold text-text-secondary tracking-wider uppercase">아델리 마켓 브리핑</span>
              </motion.div>

              <h1 className="text-[28px] font-bold leading-tight tracking-tight text-text-primary mb-3">
                오늘 시장에서 놓치면 안 되는<br />
                <span className="text-primary">{scenarioCount}가지 핵심 이야기</span>
              </h1>
              <p className="text-[13px] text-text-muted font-medium">
                과거 사례와 비교해서, 지금 어떻게 투자할지 정리했어요.
              </p>
            </div>

            {/* Scenario Cards */}
            <div className="space-y-4">
              {briefing.scenarios.slice(0, 5).map((scenario, idx) => {
                const colorSet = CARD_COLORS[idx % CARD_COLORS.length];
                const mainKeyword = briefing.main_keywords?.[idx] || '';

                return (
                  <motion.div
                    key={scenario.id}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.08, ease: [0.23, 1, 0.32, 1] }}
                    onClick={() => setSelectedScenario(scenario)}
                    className="group glass-card p-6 rounded-3xl cursor-pointer transition-all duration-300 hover:border-primary hover:translate-y-[-3px] active:scale-[0.98]"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex gap-1.5 flex-wrap">
                        {mainKeyword && (
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${colorSet.bg} ${colorSet.text}`}>
                            {mainKeyword}
                          </span>
                        )}
                        {scenario.related_companies?.slice(0, 2).map((company, ci) => (
                          <span key={ci} className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface text-text-secondary">
                            {company.name}
                          </span>
                        ))}
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-1 h-1 rounded-full bg-green-500" />
                        <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">7단계 분석</span>
                      </div>
                    </div>

                    <h3 className="text-[17px] font-bold text-text-primary mb-2 group-hover:text-primary transition-colors leading-tight tracking-tight">
                      {scenario.title?.replace(/^\[.*?\]\s*/, '') || scenario.title}
                    </h3>

                    <p className="text-[13px] text-text-secondary leading-relaxed line-clamp-2 font-medium opacity-80">
                      {scenario.summary?.replace(/<[^>]*>/g, '')}
                    </p>

                    <div className="mt-4 pt-4 border-t border-border flex items-center justify-end">
                      <div className="flex items-center text-[11px] font-bold text-primary translate-x-2 opacity-0 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                        자세히 보기
                        <svg className="ml-0.5 w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Footer Info */}
            <div className="mt-10 p-6 glass-card rounded-3xl text-center">
              <p className="text-xs text-text-muted leading-relaxed font-medium">
                과거 데이터에서 오늘의 투자 힌트를 찾아드려요.<br />
                실시간 뉴스 기반으로 분석이 진행돼요.
              </p>
            </div>

            {/* History Link */}
            <button
              onClick={() => navigate('/history')}
              className="mt-6 w-full py-3 text-xs font-bold text-text-muted hover:text-primary transition-colors"
            >
              지난 브리핑 보기
            </button>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
