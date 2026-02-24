/**
 * PrecomputedLoader — 사전 연산 데이터 로더
 * Canvas 진입 시 Redis 캐시된 분석 데이터를 먼저 표시합니다.
 */

export default function PrecomputedLoader({ data, isLoading, isCached, onCTAClick }) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-2 w-2 rounded-full bg-[#FF6B00] animate-bounce"
              style={{ animationDelay: `${i * 0.18}s` }}
            />
          ))}
        </div>
        <p className="mt-3 text-[13px] text-[#6B7684]">분석 데이터 불러오는 중...</p>
      </div>
    );
  }

  if (!data || !isCached) return null;

  return (
    <div className="space-y-3">
      {/* 캐시 배지 */}
      <div className="flex items-center gap-1.5">
        <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[11px] font-medium text-green-700">
          사전 분석 완료
        </span>
        {data.generated_at && (
          <span className="text-[11px] text-[#B0B8C1]">
            {new Date(data.generated_at).toLocaleTimeString('ko-KR', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        )}
      </div>

      {/* 분석 텍스트 */}
      {data.analysis_md && (
        <div className="rounded-xl bg-white px-4 py-3 shadow-sm">
          <div className="prose prose-sm max-w-none text-[13px] leading-relaxed text-[#191F28]">
            {data.analysis_md}
          </div>
        </div>
      )}

      {/* CTA 버튼 */}
      {data.ctas?.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {data.ctas.map((cta) => (
            <button
              key={cta.id}
              onClick={() => onCTAClick?.(cta)}
              className="rounded-xl border border-[#FF6B00]/20 bg-[#FFF7F0] px-3 py-2.5 text-left transition-colors hover:border-[#FF6B00]/40 hover:bg-[#FFF0E5]"
            >
              <span className="block text-[13px] font-medium text-[#FF6B00]">
                {cta.label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
