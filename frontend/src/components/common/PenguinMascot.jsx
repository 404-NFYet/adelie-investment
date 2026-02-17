/**
 * PenguinMascot - 펭귄 마스코트 컴포넌트
 *
 * variant에 따라 다른 애니메이션 표시:
 * - loading/empty: 5마리 펭귄 눈 뿌리기 + 빗자루 애니메이션
 * - welcome: 바운스
 * - error: 흔들기
 */

const VARIANTS = {
  welcome: { message: '안녕하세요! 무엇이든 물어보세요.', animate: 'bounce', showScene: false },
  empty:   { message: '아직 데이터가 없어요.', animate: 'none', showScene: true },
  error:   { message: '오류가 발생했어요.', animate: 'shake', showScene: false },
  loading: { message: '준비 중이에요...', animate: 'pulse', showScene: true },
};

/* 눈 뿌리기 + 빗자루 치우기 SVG 애니메이션 장면 */
function PenguinSnowScene() {
  // 눈 입자 20개 (랜덤 위치/지연)
  const snowflakes = Array.from({ length: 20 }, (_, i) => ({
    id: i,
    cx: 30 + Math.random() * 200,
    delay: Math.random() * 3,
    dur: 2 + Math.random() * 2,
    r: 1.5 + Math.random() * 2,
  }));

  return (
    <div className="relative w-64 h-36 mx-auto mb-2">
      <svg viewBox="0 0 260 140" className="w-full h-full">
        {/* 배경 */}
        <rect width="260" height="140" fill="transparent" />

        {/* 눈 입자 떨어지기 */}
        {snowflakes.map((s) => (
          <circle key={s.id} cx={s.cx} cy={-5} r={s.r} fill="white" opacity="0.7">
            <animate
              attributeName="cy" from="-5" to="130"
              dur={`${s.dur}s`} begin={`${s.delay}s`} repeatCount="indefinite"
            />
            <animate
              attributeName="opacity" values="0.7;0.3;0"
              dur={`${s.dur}s`} begin={`${s.delay}s`} repeatCount="indefinite"
            />
          </circle>
        ))}

        {/* 바닥 눈 */}
        <ellipse cx="130" cy="128" rx="120" ry="8" fill="#E8EDF2" opacity="0.5" />

        {/* 앞줄 4마리 펭귄 (눈 뿌리기) */}
        {[50, 90, 130, 170].map((x, i) => (
          <g key={i} transform={`translate(${x}, 85)`}>
            {/* 몸통 */}
            <ellipse cx="0" cy="18" rx="12" ry="16" fill="#2D3436" />
            <ellipse cx="0" cy="18" rx="8" ry="12" fill="white" />
            {/* 머리 */}
            <circle cx="0" cy="2" r="10" fill="#2D3436" />
            {/* 눈 */}
            <circle cx="-3" cy="0" r="2" fill="white" />
            <circle cx="3" cy="0" r="2" fill="white" />
            <circle cx="-3" cy="0" r="1" fill="#2D3436" />
            <circle cx="3" cy="0" r="1" fill="#2D3436" />
            {/* 부리 */}
            <polygon points="-2,4 2,4 0,7" fill="#FF6B00" />
            {/* 팔 (눈 뿌리는 모션) */}
            <line x1="-10" y1="14" x2="-18" y2="6" stroke="#2D3436" strokeWidth="3" strokeLinecap="round">
              <animateTransform
                attributeName="transform" type="rotate"
                values="-10 -10 14; 15 -10 14; -10 -10 14"
                dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite"
              />
            </line>
            <line x1="10" y1="14" x2="18" y2="6" stroke="#2D3436" strokeWidth="3" strokeLinecap="round">
              <animateTransform
                attributeName="transform" type="rotate"
                values="10 10 14; -15 10 14; 10 10 14"
                dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite"
              />
            </line>
            {/* 발 */}
            <ellipse cx="-5" cy="34" rx="5" ry="2" fill="#FF6B00" />
            <ellipse cx="5" cy="34" rx="5" ry="2" fill="#FF6B00" />
          </g>
        ))}

        {/* 뒤에 1마리 펭귄 (빗자루 치우기) */}
        <g transform="translate(220, 78)">
          {/* 몸통 */}
          <ellipse cx="0" cy="18" rx="11" ry="14" fill="#2D3436" />
          <ellipse cx="0" cy="18" rx="7" ry="10" fill="white" />
          {/* 머리 */}
          <circle cx="0" cy="4" r="9" fill="#2D3436" />
          {/* 눈 (집중 표정) */}
          <circle cx="-3" cy="2" r="1.8" fill="white" />
          <circle cx="3" cy="2" r="1.8" fill="white" />
          <circle cx="-2.5" cy="2" r="0.9" fill="#2D3436" />
          <circle cx="2.5" cy="2" r="0.9" fill="#2D3436" />
          {/* 부리 */}
          <polygon points="-1.5,5 1.5,5 0,7.5" fill="#FF6B00" />
          {/* 빗자루 */}
          <g>
            <animateTransform
              attributeName="transform" type="translate"
              values="0,0; -8,0; 0,0; 8,0; 0,0"
              dur="1.2s" repeatCount="indefinite"
            />
            <line x1="-12" y1="16" x2="-12" y2="40" stroke="#8B6914" strokeWidth="2" />
            {/* 빗자루 머리 */}
            <rect x="-20" y="38" width="16" height="4" rx="1" fill="#A0522D" />
            <line x1="-20" y1="42" x2="-20" y2="46" stroke="#8B6914" strokeWidth="1" />
            <line x1="-16" y1="42" x2="-16" y2="46" stroke="#8B6914" strokeWidth="1" />
            <line x1="-12" y1="42" x2="-12" y2="46" stroke="#8B6914" strokeWidth="1" />
            <line x1="-8" y1="42" x2="-8" y2="46" stroke="#8B6914" strokeWidth="1" />
          </g>
          {/* 발 */}
          <ellipse cx="-4" cy="32" rx="4" ry="2" fill="#FF6B00" />
          <ellipse cx="4" cy="32" rx="4" ry="2" fill="#FF6B00" />
        </g>
      </svg>
    </div>
  );
}

export default function PenguinMascot({ variant = 'empty', message = null, action = null }) {
  const config = VARIANTS[variant] || VARIANTS.empty;
  const displayMessage = message || config.message;

  const animationClass = {
    bounce: 'animate-penguin-bounce',
    shake: 'animate-wobble',
    pulse: 'animate-pulse',
    none: '',
  }[config.animate];

  return (
    <div className="flex flex-col items-center py-4">
      {config.showScene ? (
        <PenguinSnowScene />
      ) : (
        <img
          src="/images/penguin-3d.webp"
          alt="펭귄 마스코트"
          className={`w-20 h-20 object-contain mb-3 ${animationClass}`}
        />
      )}
      <p className="text-sm text-text-secondary text-center">{displayMessage}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
