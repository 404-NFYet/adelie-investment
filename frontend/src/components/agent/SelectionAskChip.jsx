export default function SelectionAskChip({
  visible = false,
  left = 0,
  top = 0,
  onAsk,
  label = '이 부분 질문',
}) {
  if (!visible) return null;

  return (
    <button
      type="button"
      onMouseDown={(event) => event.preventDefault()}
      onClick={onAsk}
      className="fixed z-40 -translate-x-1/2 rounded-full border border-[#E8EBED] bg-white/92 px-3 py-1.5 text-[12px] font-semibold text-[#191F28] shadow-[0_8px_20px_rgba(15,23,42,0.12)] backdrop-blur-sm active:scale-95"
      style={{ left: `${left}px`, top: `${top}px` }}
      aria-label="선택한 텍스트 질문하기"
    >
      {label}
    </button>
  );
}
