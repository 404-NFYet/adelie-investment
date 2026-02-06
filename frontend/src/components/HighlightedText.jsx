/**
 * HighlightedText.jsx - AI 생성 콘텐츠 내 어려운 용어 하이라이팅
 * [[용어]] 형식의 마킹된 텍스트를 파싱하여 클릭 가능한 하이라이트로 렌더링
 */
import { useTutor } from '../contexts/TutorContext';

export default function HighlightedText({ content, onTermClick }) {
  const { openTutor } = useTutor();

  // [[term]] 패턴을 찾아 하이라이트 처리
  const parseContent = (text) => {
    const pattern = /\[\[([^\]]+)\]\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(text)) !== null) {
      // 일반 텍스트 추가
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: text.slice(lastIndex, match.index),
        });
      }

      // 하이라이트 용어 추가
      parts.push({
        type: 'term',
        content: match[1],
      });

      lastIndex = match.index + match[0].length;
    }

    // 남은 텍스트 추가
    if (lastIndex < text.length) {
      parts.push({
        type: 'text',
        content: text.slice(lastIndex),
      });
    }

    return parts;
  };

  const handleTermClick = (term) => {
    if (onTermClick) {
      onTermClick(term);
    } else {
      openTutor(term);
    }
  };

  const parts = parseContent(content || '');

  return (
    <span>
      {parts.map((part, index) => {
        if (part.type === 'term') {
          return (
            <span
              key={index}
              className="term-highlight"
              onClick={() => handleTermClick(part.content)}
              title="클릭하여 설명 보기"
            >
              {part.content}
            </span>
          );
        }
        return <span key={index}>{part.content}</span>;
      })}
    </span>
  );
}
