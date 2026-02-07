/**
 * Leaderboard.jsx - 수익률 리더보드
 */
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { portfolioApi } from '../../api';

const MEDALS = ['', '1st', '2nd', '3rd'];

function formatKRW(value) {
  return new Intl.NumberFormat('ko-KR').format(Math.round(value)) + '원';
}

export default function Leaderboard({ userId }) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    portfolioApi.getLeaderboard(userId)
      .then(d => setData(d))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, [userId]);

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <div className="animate-pulse text-text-secondary">랭킹 불러오는 중...</div>
      </div>
    );
  }

  if (!data || data.rankings.length === 0) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="card text-center py-8">
        <p className="text-3xl mb-3">🏆</p>
        <p className="text-text-secondary text-sm">아직 랭킹 데이터가 없습니다</p>
        <p className="text-text-muted text-xs mt-1">투자를 시작하면 순위가 표시됩니다</p>
      </motion.div>
    );
  }

  return (
    <div className="space-y-3">
      {/* 내 순위 카드 */}
      {data.my_entry && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card border-2 border-primary"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span className="text-sm font-bold text-primary">{data.my_rank}위</span>
              </div>
              <div>
                <p className="font-bold text-sm">내 순위</p>
                <p className="text-xs text-text-secondary">{data.my_entry.username}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold text-sm">{formatKRW(data.my_entry.total_value)}</p>
              <p className={`text-xs font-semibold ${data.my_entry.profit_loss_pct > 0 ? 'text-red-500' : data.my_entry.profit_loss_pct < 0 ? 'text-blue-500' : 'text-text-secondary'}`}>
                {data.my_entry.profit_loss_pct > 0 ? '+' : ''}{data.my_entry.profit_loss_pct}%
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* TOP N 리스트 */}
      <div className="card">
        <h3 className="font-bold text-sm mb-3">전체 순위</h3>
        <div className="space-y-1">
          {data.rankings.map((entry, i) => (
            <motion.div
              key={entry.user_id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`flex items-center justify-between py-2.5 px-2 rounded-lg transition-colors ${
                entry.is_me ? 'bg-primary/5' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="w-6 text-center">
                  {entry.rank <= 3 ? (
                    <span className="text-base">{entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : '🥉'}</span>
                  ) : (
                    <span className="text-xs font-bold text-text-muted">{entry.rank}</span>
                  )}
                </span>
                <p className={`text-sm ${entry.is_me ? 'font-bold text-primary' : 'font-medium'}`}>
                  {entry.username}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold">{formatKRW(entry.total_value)}</p>
                <p className={`text-xs font-medium ${entry.profit_loss_pct > 0 ? 'text-red-500' : entry.profit_loss_pct < 0 ? 'text-blue-500' : 'text-text-secondary'}`}>
                  {entry.profit_loss_pct > 0 ? '+' : ''}{entry.profit_loss_pct}%
                </p>
              </div>
            </motion.div>
          ))}
        </div>
        <p className="text-xs text-text-muted text-center mt-3">총 {data.total_users}명 참여</p>
      </div>
    </div>
  );
}
