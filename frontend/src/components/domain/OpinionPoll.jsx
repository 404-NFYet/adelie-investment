/**
 * OpinionPoll.jsx - 의견 투표 카드
 * 두 가지 선택지를 제시하여 사용자의 의견을 수집
 */
import { useState } from 'react';

export default function OpinionPoll({ question, options = [], onSelect }) {
  const [selected, setSelected] = useState(null);

  const handleSelect = (optionId) => {
    setSelected(optionId);
    if (onSelect) onSelect(optionId);
  };

  return (
    <div className="rounded-card p-5 my-6 border-2 border-primary/40 bg-surface-elevated">
      <h4 className="text-base font-bold mb-1">당신의 생각은?</h4>
      <p className="text-sm text-text-secondary mb-4">{question}</p>
      <div className="flex gap-3">
        {options.map((option) => (
          <button
            key={option.id}
            onClick={() => handleSelect(option.id)}
            className={`flex-1 py-3 px-4 rounded-xl text-sm font-semibold transition-all duration-200 border-2
              ${
                selected === option.id
                  ? 'border-primary bg-primary text-white scale-[1.02]'
                  : 'border-border bg-surface text-text-primary hover:border-primary/50'
              }`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
