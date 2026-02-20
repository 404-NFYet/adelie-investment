import React from 'react';

const HIGHLIGHT_PATTERN = /<mark\b([^>]*)>(.*?)<\/mark>|\[\[([^\]]+)\]\]/gis;

function pushText(nodes, value) {
  if (!value) return;
  nodes.push({ type: 'text', value });
}

export default function TermHighlighter({ content, onClickTerm }) {
  const text = String(content || '');
  const nodes = [];
  let lastIndex = 0;
  let match;

  while ((match = HIGHLIGHT_PATTERN.exec(text)) !== null) {
    const idx = match.index;
    if (idx > lastIndex) {
      pushText(nodes, text.slice(lastIndex, idx));
    }

    const markAttrs = match[1];
    const markInner = match[2];
    const bracketTerm = match[3];

    if (markInner != null) {
      const termFromAttr = /data-term=['"]([^'"]+)['"]/i.exec(markAttrs || '')?.[1];
      const kindFromAttr = /data-kind=['"]([^'"]+)['"]/i.exec(markAttrs || '')?.[1];
      const term = (termFromAttr || markInner || '').trim();
      nodes.push({
        type: 'term',
        value: term,
        display: markInner,
        kind: kindFromAttr || 'word',
      });
    } else if (bracketTerm != null) {
      const term = bracketTerm.trim();
      nodes.push({ type: 'term', value: term, display: term, kind: 'word' });
    }

    lastIndex = idx + match[0].length;
  }

  if (lastIndex < text.length) {
    pushText(nodes, text.slice(lastIndex));
  }

  return (
    <div className="rich-highlight">
      {nodes.map((node, idx) => {
        if (node.type === 'term') {
          return (
            <button
              type="button"
              className={node.kind === 'phrase' ? 'term-inline phrase' : 'term-inline word'}
              key={`${node.value}-${idx}`}
              onClick={() => onClickTerm?.(node.value)}
            >
              {node.display || node.value}
            </button>
          );
        }
        return <span key={`text-${idx}`}>{node.value}</span>;
      })}
    </div>
  );
}
