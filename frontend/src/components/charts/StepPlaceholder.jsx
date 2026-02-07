/**
 * StepPlaceholder.jsx - 스텝별 SVG 플레이스홀더 그래픽
 * 차트 데이터가 없을 때 표시되는 시각적 플레이스홀더
 */

const STEP_GRAPHICS = {
  background: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <polyline points="10,80 40,60 80,70 120,40 160,50 190,20" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
      <circle cx="190" cy="20" r="5" fill={color} />
      <text x="100" y="95" textAnchor="middle" fontSize="10" fill="#8B95A1">시장 추세</text>
    </svg>
  ),
  mirroring: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <polyline points="10,50 50,30 90,60 130,20" fill="none" stroke="#8B95A1" strokeWidth="2" strokeDasharray="5,5" />
      <polyline points="70,50 110,30 150,60 190,20" fill="none" stroke={color} strokeWidth="3" />
      <text x="50" y="95" textAnchor="middle" fontSize="9" fill="#8B95A1">과거</text>
      <text x="150" y="95" textAnchor="middle" fontSize="9" fill={color}>현재</text>
    </svg>
  ),
  difference: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <rect x="30" y="30" width="50" height="50" rx="8" fill="#E5E8EB" />
      <rect x="120" y="20" width="50" height="60" rx="8" fill={color} opacity="0.3" />
      <line x1="95" y1="50" x2="110" y2="50" stroke={color} strokeWidth="2" markerEnd="url(#arrow)" />
      <text x="55" y="95" textAnchor="middle" fontSize="9" fill="#8B95A1">과거</text>
      <text x="145" y="95" textAnchor="middle" fontSize="9" fill={color}>현재</text>
    </svg>
  ),
  devils_advocate: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <circle cx="100" cy="45" r="30" fill="none" stroke="#EF4444" strokeWidth="2" />
      <text x="100" y="50" textAnchor="middle" fontSize="24" fill="#EF4444">!</text>
      <text x="100" y="90" textAnchor="middle" fontSize="9" fill="#8B95A1">반대 시나리오</text>
    </svg>
  ),
  simulation: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <rect x="20" y="20" width="160" height="60" rx="8" fill="none" stroke={color} strokeWidth="2" />
      <text x="100" y="40" textAnchor="middle" fontSize="10" fill="#4E5968">1,000만원</text>
      <polyline points="40,55 70,50 100,60 130,45 160,48" fill="none" stroke={color} strokeWidth="2" />
      <text x="100" y="90" textAnchor="middle" fontSize="9" fill="#8B95A1">모의 투자</text>
    </svg>
  ),
  result: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <rect x="30" y="60" width="25" height="20" rx="3" fill="#E5E8EB" />
      <rect x="65" y="40" width="25" height="40" rx="3" fill="#E5E8EB" />
      <rect x="100" y="25" width="25" height="55" rx="3" fill={color} />
      <rect x="135" y="35" width="25" height="45" rx="3" fill={color} opacity="0.6" />
      <text x="100" y="95" textAnchor="middle" fontSize="9" fill="#8B95A1">투자 결과</text>
    </svg>
  ),
  action: (color) => (
    <svg viewBox="0 0 200 100" className="w-full h-full">
      <circle cx="100" cy="45" r="25" fill={color} opacity="0.15" />
      <text x="100" y="50" textAnchor="middle" fontSize="20">🚀</text>
      <text x="100" y="90" textAnchor="middle" fontSize="9" fill={color}>액션 플랜</text>
    </svg>
  ),
};

export default function StepPlaceholder({ stepKey, color = '#FF6B00', className = '' }) {
  const graphic = STEP_GRAPHICS[stepKey];

  return (
    <div className={`h-36 bg-gray-50/50 dark:bg-gray-800/20 rounded-xl flex items-center justify-center p-4 ${className}`}>
      {graphic ? graphic(color) : (
        <p className="text-xs text-gray-400">차트 준비 중...</p>
      )}
    </div>
  );
}
