/**
 * HighlightedText.jsx - AI 생성 콘텐츠 내 용어 하이라이팅
 * <mark class='term'>용어</mark> 및 [[용어]] 형식을 모두 지원.
 * 클릭하면 TermBottomSheet에서 LLM 동적 설명을 표시.
 * 마크다운(**bold**, *italic* 등)은 ReactMarkdown으로 처리.
 */
import ReactMarkdown from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import remarkMath from 'remark-math';
import { useTermContext } from '../../contexts/TermContext';

export default function HighlightedText({ content, onTermClick }) {
  const { openTermSheet } = useTermContext();

  // <mark class='term'>term</mark> 및 [[term]] 패턴을 모두 파싱
  const parseContent = (text) => {
    const pattern = /<mark\s+class=['"]term(?:-highlight)?['"]>(.*?)<\/mark>|\[\[([^\]]+)\]\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(text)) !== null) {
      // 일반 텍스트 추가
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
      }

      // 하이라이트 용어 추가 (그룹 1 또는 그룹 2)
      const term = match[1] || match[2];
      parts.push({ type: 'term', content: term });

      lastIndex = match.index + match[0].length;
    }

    // 남은 텍스트 추가
    if (lastIndex < text.length) {
      parts.push({ type: 'text', content: text.slice(lastIndex) });
    }

    return parts;
  };

  const handleTermClick = (term) => {
    if (onTermClick) {
      onTermClick(term);
    } else {
      openTermSheet(term);
    }
  };

  const parts = parseContent(content || '');

  return (
    <span>
      {parts.map((part, index) => {
        if (part.type === 'term') {
          return (
            <mark
              key={index}
              className="term-highlight"
              onClick={() => handleTermClick(part.content)}
              title="클릭하여 설명 보기"
            >
              {part.content}
            </mark>
          );
        }
        return (
          <ReactMarkdown
            key={index}
            remarkPlugins={[remarkMath]}
            rehypePlugins={[rehypeRaw, rehypeKatex]}
            components={{
              // 인라인 컨텍스트이므로 p → span 변환
              p: ({ children }) => <span>{children}</span>,
            }}
          >
            {part.content.replace(/->/g, '→')}
          </ReactMarkdown>
        );
      })}
    </span>
  );
}
