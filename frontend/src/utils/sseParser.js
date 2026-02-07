/**
 * SSE (Server-Sent Events) 라인 파서
 *
 * SSE 스트림의 청크를 줄 단위로 분리하고,
 * `data: ` 접두사를 파싱하여 JSON 객체를 반환한다.
 */

/**
 * SSE 청크 버퍼에서 완성된 라인들을 추출한다.
 * @param {string} buffer - 현재 버퍼
 * @param {string} newChunk - 새로 수신된 청크
 * @returns {{ lines: string[], remaining: string }} 완성된 라인과 남은 버퍼
 */
export function extractLines(buffer, newChunk) {
  const combined = buffer + newChunk;
  const parts = combined.split('\n');
  const remaining = parts.pop() || '';
  return { lines: parts, remaining };
}

/**
 * SSE 라인에서 데이터를 파싱한다.
 * @param {string} line - SSE 라인
 * @returns {object|null} 파싱된 JSON 객체 또는 null
 */
export function parseSSELine(line) {
  const trimmed = line.trim();
  if (!trimmed || !trimmed.startsWith('data: ')) return null;
  try {
    return JSON.parse(trimmed.slice(6));
  } catch {
    return null;
  }
}
