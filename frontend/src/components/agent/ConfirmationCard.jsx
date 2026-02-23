/**
 * ConfirmationCard - 확인 요청 카드
 * 
 * 에이전트가 액션 실행 전 유저에게 확인을 요청하는 UI
 */
import { motion } from 'framer-motion';

export default function ConfirmationCard({ action, onConfirm, onReject }) {
  const riskColors = {
    low: { bg: 'bg-[#E8F5E9]', border: 'border-[#A5D6A7]', icon: '✓' },
    medium: { bg: 'bg-[#FFF8E1]', border: 'border-[#FFCC80]', icon: '!' },
    high: { bg: 'bg-[#FFEBEE]', border: 'border-[#EF9A9A]', icon: '⚠' },
  };

  const risk = action.risk || 'medium';
  const colors = riskColors[risk];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-4 mb-4"
    >
      <div className={`${colors.bg} ${colors.border} border rounded-2xl p-4`}>
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center flex-shrink-0 text-lg">
            {colors.icon}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-[#191F28] text-sm mb-1">
              {action.title || '실행 확인'}
            </h4>
            <p className="text-sm text-[#4E5968] leading-relaxed">
              {action.description || `"${action.actionId}" 명령을 실행할까요?`}
            </p>
            {action.params && Object.keys(action.params).length > 0 && (
              <div className="mt-2 p-2 bg-white/50 rounded-lg">
                <p className="text-xs text-[#8B95A1] mb-1">매개변수:</p>
                {Object.entries(action.params).map(([key, val]) => (
                  <p key={key} className="text-xs text-[#4E5968]">
                    <span className="font-medium">{key}:</span> {String(val)}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <button
            onClick={onReject}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-[#4E5968] bg-white border border-[#E5E8EB] rounded-xl hover:bg-[#F7F8FA] transition-colors"
          >
            취소
          </button>
          <button
            onClick={() => onConfirm(action)}
            className="flex-1 px-4 py-2.5 text-sm font-medium text-white bg-[#FF6B00] rounded-xl hover:bg-[#E55F00] transition-colors"
          >
            실행
          </button>
        </div>
      </div>
    </motion.div>
  );
}
