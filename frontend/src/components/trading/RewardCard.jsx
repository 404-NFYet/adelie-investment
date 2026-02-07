/**
 * RewardCard.jsx - 보상 상태 카드
 */
import { motion } from 'framer-motion';

function formatKRW(val) {
  return new Intl.NumberFormat('ko-KR').format(Math.round(val)) + '원';
}

const STATUS_LABELS = {
  pending: { label: '대기 중', color: 'text-yellow-600 bg-yellow-50', icon: '⏳' },
  applied: { label: '보너스 적용', color: 'text-green-600 bg-green-50', icon: '🎉' },
  expired: { label: '보너스 소멸', color: 'text-gray-500 bg-gray-50', icon: '⏰' },
};

export default function RewardCard({ reward }) {
  const status = STATUS_LABELS[reward.status] || STATUS_LABELS.pending;
  const maturityDate = reward.maturity_at ? new Date(reward.maturity_at) : null;
  const now = new Date();
  const daysLeft = maturityDate ? Math.max(0, Math.ceil((maturityDate - now) / (1000 * 60 * 60 * 24))) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-4"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xl">{status.icon}</span>
          <div>
            <p className="font-semibold text-sm">브리핑 보상</p>
            <p className="text-xs text-gray-500">
              {reward.created_at ? new Date(reward.created_at).toLocaleDateString('ko-KR') : ''}
            </p>
          </div>
        </div>
        <span className={`text-xs font-medium px-2 py-1 rounded-full ${status.color}`}>
          {status.label}
        </span>
      </div>

      <div className="flex justify-between items-end">
        <div>
          <p className="text-xs text-gray-500">기본 보상</p>
          <p className="font-bold">{formatKRW(reward.base_reward)}</p>
        </div>
        {reward.status === 'pending' && daysLeft > 0 && (
          <div className="text-right">
            <p className="text-xs text-gray-500">멀티플라이어 만기</p>
            <p className="text-sm font-semibold text-primary">{daysLeft}일 남음</p>
          </div>
        )}
        {reward.status === 'applied' && (
          <div className="text-right">
            <p className="text-xs text-gray-500">최종 보상</p>
            <p className="font-bold text-green-600">{formatKRW(reward.final_reward)}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
