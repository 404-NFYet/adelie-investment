/**
 * NextStepButton.jsx - 하단 고정 NEXT STEP 버튼
 * 페이지 하단에 고정되어 다음 단계로 이동하는 버튼
 */
export default function NextStepButton({ onClick, label = 'NEXT STEP' }) {
  return (
    <div className="fixed bottom-8 left-0 right-0 flex justify-center z-30">
      <button
        onClick={onClick}
        className="btn-primary px-12 py-4 rounded-full text-sm font-bold tracking-wider"
      >
        {label}
      </button>
    </div>
  );
}
