function formatPointValue(value) {
  return `${Number(value || 0).toLocaleString('ko-KR')}p`;
}

const COPY = {
  success: {
    heading: '축하합니다',
    prefix: '모의투자에 사용할 수 있는',
    suffix: '를 받았어요',
    cta: '모의투자 하러 가기',
    image: '/images/reward-success-penguin.png',
    imageAlt: '보상 축하 캐릭터',
  },
  already_claimed: {
    heading: '보상을 이미 받았어요',
    prefix: '해당 브리핑 보상은',
    suffix: '1회만 지급됩니다',
    cta: '포트폴리오로 이동',
    image: '/images/penguin-3d.png',
    imageAlt: '보상 안내 캐릭터',
  },
};

export default function RewardResultScreen({
  mode = 'success',
  rewardAmount = 100000,
  onBack,
  onPrimaryAction,
}) {
  const content = COPY[mode] || COPY.success;
  const backgroundClass = mode === 'already_claimed' ? 'bg-white' : 'bg-[#efefef]';

  return (
    <section className={`fixed inset-0 z-50 ${backgroundClass}`}>
      <div className="mx-auto flex min-h-screen w-full max-w-mobile flex-col px-5 pb-8 pt-16">
        <button
          type="button"
          onClick={onBack}
          className="w-fit text-xs font-semibold text-[rgba(0,0,0,0.61)]"
        >
          돌아가기
        </button>

        <div className="mt-14">
          <h2 className="text-[clamp(2.2rem,10vw,2.6rem)] font-extrabold tracking-[-0.02em] text-black">
            {content.heading}
          </h2>
          <p className="mt-5 text-[clamp(1.45rem,6vw,1.7rem)] leading-[1.2] text-black">
            {content.prefix}
            {mode === 'success' ? (
              <>
                <br />
                <strong className="font-extrabold">{formatPointValue(rewardAmount)}</strong>
                {' '}
                {content.suffix}
              </>
            ) : (
              <>
                <br />
                {content.suffix}
              </>
            )}
          </p>
        </div>

        <div className="flex flex-1 items-center justify-center py-8">
          <img
            src={content.image}
            alt={content.imageAlt}
            className="max-h-[340px] w-full max-w-[330px] object-contain"
          />
        </div>

        <button
          type="button"
          onClick={onPrimaryAction}
          className="h-[60px] w-full rounded-[20px] bg-[#ff5e00] text-[24px] font-bold text-white"
        >
          {content.cta}
        </button>
      </div>
    </section>
  );
}
