/**
 * 마크다운 텍스트를 HTML로 변환하는 경량 렌더러
 */
export function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/^### (.*$)/gm, '<h4 class="font-bold text-sm mt-3 mb-1 text-text-primary">$1</h4>')
    .replace(/^## (.*$)/gm, '<h3 class="font-bold text-base mt-3 mb-1 text-text-primary">$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-text-primary">$1</strong>')
    .replace(/`(.*?)`/g, '<code class="bg-border-light px-1.5 py-0.5 rounded text-xs font-mono text-primary">$1</code>')
    .replace(/^- (.*$)/gm, '<div class="flex gap-2 ml-2"><span class="text-primary">•</span><span>$1</span></div>')
    .replace(/^(\d+)\. (.*$)/gm, '<div class="flex gap-2 ml-2"><span class="text-primary font-semibold">$1.</span><span>$2</span></div>')
    .replace(/^---$/gm, '<hr class="border-border my-3" />')
    .replace(/\n\n/g, '</p><p class="mt-2">')
    .replace(/\n/g, '<br/>');
}
