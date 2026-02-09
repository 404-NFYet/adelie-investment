/**
 * History.jsx - 지난 브리핑 히스토리 (adelie_fe_test 스타일)
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronLeft } from 'lucide-react';
import AppHeader from '../components/layout/AppHeader';
import NarrativeView from '../components/domain/NarrativeView';
import { listBriefings, getBriefingById } from '../api/briefings';

// 날짜 포맷
function formatDate(dateStr) {
  try {
    const d = new Date(dateStr);
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
    const weekday = weekdays[d.getDay()];
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return { dateLabel: `${month}월 ${day}일 (${weekday})`, timeLabel: `${hours}:${minutes}` };
  } catch {
    return { dateLabel: dateStr, timeLabel: '' };
  }
}

// 시나리오 카드 색상
const CARD_COLORS = [
  { bg: 'bg-orange-50', text: 'text-primary' },
  { bg: 'bg-blue-50', text: 'text-blue-500' },
  { bg: 'bg-purple-50', text: 'text-purple-600' },
  { bg: 'bg-green-50', text: 'text-green-600' },
  { bg: 'bg-pink-50', text: 'text-pink-600' },
];

export default function History() {
  const navigate = useNavigate();
  const [briefingList, setBriefingList] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedBriefingId, setSelectedBriefingId] = useState(null);
  const [selectedBriefing, setSelectedBriefing] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // 브리핑 목록 로드
  useEffect(() => {
    const fetchList = async () => {
      try {
        setIsLoading(true);
        const data = await listBriefings(20, 0);
        setBriefingList(data.briefings || data || []);
      } catch (err) {
        console.error('브리핑 목록 로딩 실패:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchList();
  }, []);

  // 선택된 브리핑 상세 로드
  useEffect(() => {
    if (!selectedBriefingId) {
      setSelectedBriefing(null);
      return;
    }
    const fetchDetail = async () => {
      try {
        setIsLoadingDetail(true);
        const data = await getBriefingById(selectedBriefingId);
        setSelectedBriefing(data);
      } catch (err) {
        console.error('브리핑 상세 로딩 실패:', err);
      } finally {
        setIsLoadingDetail(false);
      }
    };
    fetchDetail();
  }, [selectedBriefingId]);

  // 내러티브 뷰 표시
  if (selectedBriefing && selectedScenario) {
    return (
      <NarrativeView
        briefing={selectedBriefing}
        scenario={selectedScenario}
        onBack={() => setSelectedScenario(null)}
      />
    );
  }

  // 브리핑 상세 (시나리오 목록)
  if (selectedBriefing && selectedBriefingId && !selectedScenario) {
    return (
      <div className="min-h-screen bg-background pb-24">
        <div className="w-full max-w-lg mx-auto p-5 pt-8">
          <button
            onClick={() => setSelectedBriefingId(null)}
            className="flex items-center gap-1 text-[13px] font-bold text-text-muted hover:text-text-primary transition-colors mb-6"
          >
            <ChevronLeft className="w-4 h-4" />
            브리핑 목록
          </button>

          <div className="mb-6">
            <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1">
              {formatDate(selectedBriefing.date).dateLabel} {formatDate(selectedBriefing.date).timeLabel}
            </p>
            <h1 className="text-[22px] font-bold text-text-primary tracking-tight">
              브리핑 상세
            </h1>
          </div>

          <div className="space-y-3">
            {selectedBriefing.scenarios?.map((scenario, idx) => {
              const colorSet = CARD_COLORS[idx % CARD_COLORS.length];
              const mainKeyword = selectedBriefing.main_keywords?.[idx] || '';

              return (
                <motion.div
                  key={scenario.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.06 }}
                  onClick={() => setSelectedScenario(scenario)}
                  className="group p-5 rounded-2xl glass-card cursor-pointer hover:border-primary hover:translate-y-[-2px] transition-all duration-300 active:scale-[0.98]"
                >
                  {mainKeyword && (
                    <div className="flex gap-1.5 flex-wrap mb-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${colorSet.bg} ${colorSet.text}`}>
                        {mainKeyword}
                      </span>
                    </div>
                  )}
                  <h3 className="text-[15px] font-bold text-text-primary group-hover:text-primary transition-colors leading-tight tracking-tight">
                    {scenario.title?.replace(/^\[.*?\]\s*/, '') || scenario.title}
                  </h3>
                  <p className="mt-1.5 text-xs text-text-muted line-clamp-2 leading-relaxed">
                    {scenario.summary?.replace(/<[^>]*>/g, '') || ''}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // 브리핑 목록
  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader title="히스토리" />

      <div className="w-full max-w-lg mx-auto p-5 pt-2">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-1 text-[13px] font-bold text-text-muted hover:text-text-primary transition-colors mb-6"
        >
          <ChevronLeft className="w-4 h-4" />
          오늘의 브리핑
        </button>

        <div className="mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full glass-card mb-4">
            <span className="text-[13px]">🐧</span>
            <span className="text-[10px] font-bold text-text-secondary tracking-wider uppercase">지난 브리핑</span>
          </div>
          <h1 className="text-[24px] font-bold text-text-primary tracking-tight">
            브리핑 히스토리
          </h1>
          <p className="text-[13px] text-text-muted mt-1">지금까지 생성된 브리핑을 확인할 수 있어요.</p>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-xs font-bold text-text-muted">불러오는 중...</p>
          </div>
        ) : !briefingList || briefingList.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-text-muted text-sm">아직 생성된 브리핑이 없어요.</p>
            <button onClick={() => navigate('/')} className="btn-primary mt-4">
              홈으로 가기
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {briefingList.map((item, idx) => {
              const { dateLabel, timeLabel } = formatDate(item.date);
              const isFirst = idx === 0;

              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  onClick={() => setSelectedBriefingId(item.id)}
                  className={`group p-5 rounded-2xl border cursor-pointer hover:translate-y-[-2px] transition-all duration-300 active:scale-[0.98] ${
                    isFirst
                      ? 'glass-card border-primary/20 hover:border-primary'
                      : 'glass-card hover:border-text-muted'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-bold text-text-primary">{dateLabel}</span>
                      {timeLabel && (
                        <span className="text-[11px] text-text-muted font-medium">{timeLabel}</span>
                      )}
                    </div>
                    {isFirst && (
                      <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-primary text-white uppercase tracking-wider">
                        Latest
                      </span>
                    )}
                  </div>

                  {item.main_keywords?.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap mb-2">
                      {item.main_keywords.slice(0, 3).map(kw => (
                        <span key={kw} className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-surface text-text-secondary">
                          {kw}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="space-y-1">
                    {item.scenarios?.slice(0, 3).map((scenario, tidx) => (
                      <p key={tidx} className="text-xs text-text-muted leading-relaxed truncate">
                        {scenario.title?.replace(/^\[.*?\]\s*/, '') || scenario.title}
                      </p>
                    ))}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
