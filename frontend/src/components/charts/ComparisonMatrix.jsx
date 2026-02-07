export default function ComparisonMatrix({ data }) {
  if (!data?.points?.length) return <div className="flex items-center justify-center h-full text-xs text-text-muted">비교 데이터 준비 중...</div>;
  const badgeColor = (s) => s === '유사' ? 'bg-green-100 text-green-700' : s === '상이' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700';
  return (
    <div className="w-full h-full overflow-y-auto px-1">
      <table className="w-full text-xs">
        <thead><tr className="text-text-muted">
          <th className="text-left py-1 font-semibold w-1/4">관점</th>
          <th className="text-left py-1 font-semibold w-1/3">과거</th>
          <th className="text-left py-1 font-semibold w-1/3">현재</th>
        </tr></thead>
        <tbody>
          {data.points.map((p, i) => (
            <tr key={i} className="border-t border-border-light">
              <td className="py-2 font-medium text-text-primary">{p.aspect} <span className={`inline-block ml-1 px-1.5 py-0.5 rounded text-[9px] font-bold ${badgeColor(p.similarity)}`}>{p.similarity}</span></td>
              <td className="py-2 text-text-secondary">{p.past}</td>
              <td className="py-2 text-text-secondary">{p.present}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
