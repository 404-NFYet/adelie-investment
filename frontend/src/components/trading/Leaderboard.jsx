/**
 * Leaderboard.jsx - 수익률 리더보드
 */
import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { portfolioApi } from '../../api';
import { formatKRW } from '../../utils/formatNumber';

const PAGE_SIZE = 20;

export default function Leaderboard({ userId }) {
  const [rankings, setRankings] = useState([]);
  const [myRank, setMyRank] = useState(null);
  const [myEntry, setMyEntry] = useState(null);
  const [totalUsers, setTotalUsers] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchPage = useCallback(async (pageOffset, append = false) => {
    const d = await portfolioApi.getLeaderboard(PAGE_SIZE, pageOffset);
    if (append) {
      setRankings(prev => [...prev, ...d.rankings]);
    } else {
      setRankings(d.rankings);
      setMyRank(d.my_rank);
      setMyEntry(d.my_entry);
      setTotalUsers(d.total_users);
    }
    setHasMore(d.has_more);
    setOffset(pageOffset);
  }, []);

  useEffect(() => {
    setIsLoading(true);
    fetchPage(0)
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [userId, fetchPage]);

  const loadMore = async () => {
    const nextOffset = offset + PAGE_SIZE;
    setIsLoadingMore(true);
    try {
      await fetchPage(nextOffset, true);
    } catch {
      // 에러 무시
    } finally {
      setIsLoadingMore(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-pulse text-text-secondary">랭킹 불러오는 중...</div>
      </div>
    );
  }

  if (rankings.length === 0) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-8">
        <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-primary/10 flex items-center justify-center text-primary">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" /><path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" /><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" /><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
          </svg>
        </div>
        <p className="text-text-secondary text-sm">아직 랭킹 데이터가 없습니다</p>
        <p className="text-text-muted text-xs mt-1">투자를 시작하면 순위가 표시됩니다</p>
      </motion.div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 내 순위 카드 */}
      {myEntry && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card border-2 border-primary"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-sm font-bold text-primary">{myRank}위</span>
              </div>
              <div>
                <p className="font-bold text-sm">내 순위</p>
                <p className="text-xs text-text-secondary">{myEntry.username}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold text-sm">{formatKRW(myEntry.total_value)}</p>
              <p className={`text-xs font-semibold ${myEntry.profit_loss_pct > 0 ? 'text-red-500' : myEntry.profit_loss_pct < 0 ? 'text-blue-500' : 'text-text-secondary'}`}>
                {myEntry.profit_loss_pct > 0 ? '+' : ''}{Number(myEntry.profit_loss_pct).toFixed(2)}%
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* TOP N 리스트 */}
      <div className="card">
        <h3 className="font-bold text-sm mb-3">전체 순위</h3>
        <div className="space-y-1">
          {rankings.map((entry, i) => (
            <motion.div
              key={entry.user_id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: Math.min(i, 19) * 0.05 }}
              className={`flex items-center justify-between py-2.5 px-2 rounded-lg transition-colors ${
                entry.is_me ? 'bg-primary/5' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="w-6 text-center">
                  {entry.rank <= 3 ? (
                    <span className={`text-xs font-bold ${entry.rank === 1 ? 'text-yellow-500' : entry.rank === 2 ? 'text-gray-400' : 'text-amber-600'}`}>{entry.rank}</span>
                  ) : (
                    <span className="text-xs font-bold text-text-muted">{entry.rank}</span>
                  )}
                </span>
                <p className={`text-sm ${entry.is_me ? 'font-bold text-primary' : 'font-medium'}`}>
                  {entry.username}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold">{entry.is_me ? formatKRW(entry.total_value) : '-'}</p>
                <p className={`text-xs font-medium ${entry.profit_loss_pct > 0 ? 'text-red-500' : entry.profit_loss_pct < 0 ? 'text-blue-500' : 'text-text-secondary'}`}>
                  {entry.profit_loss_pct > 0 ? '+' : ''}{Number(entry.profit_loss_pct).toFixed(2)}%
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* 더보기 버튼 */}
        {hasMore && (
          <button
            onClick={loadMore}
            disabled={isLoadingMore}
            className="w-full mt-3 py-2 text-sm font-medium text-primary hover:bg-primary/5 rounded-lg transition-colors disabled:opacity-50"
          >
            {isLoadingMore ? '불러오는 중...' : '더보기'}
          </button>
        )}

        <p className="text-xs text-text-muted text-center mt-3">총 {totalUsers}명 참여</p>
      </div>
    </div>
  );
}
