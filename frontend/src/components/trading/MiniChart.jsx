/**
 * MiniChart.jsx - 미니 라인 차트 (Chart.js)
 */
import { useMemo } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
} from 'chart.js';

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip);

function parseNumeric(value) {
  if (typeof value === 'number') return value;
  if (typeof value === 'string') return Number(value.replace(/,/g, ''));
  return Number(value);
}

export default function MiniChart({ dates = [], values = [], color = '#4F46E5', height = 80 }) {
  const normalized = useMemo(() => {
    const sourceDates = Array.isArray(dates) ? dates : [];
    const sourceValues = Array.isArray(values) ? values : [];
    const pairs = [];

    for (let idx = 0; idx < sourceValues.length; idx += 1) {
      const value = parseNumeric(sourceValues[idx]);
      if (!Number.isFinite(value)) continue;
      pairs.push({
        label: sourceDates[idx] ?? `${idx + 1}`,
        value,
      });
    }

    return {
      labels: pairs.map((p) => p.label),
      values: pairs.map((p) => p.value),
    };
  }, [dates, values]);

  const isPositive = normalized.values.length >= 2
    && normalized.values[normalized.values.length - 1] >= normalized.values[0];
  const lineColor = color === 'auto' ? (isPositive ? '#EF4444' : '#3B82F6') : color;

  const data = useMemo(() => ({
    labels: normalized.labels,
    datasets: [{
      data: normalized.values,
      borderColor: lineColor,
      backgroundColor: lineColor + '20',
      borderWidth: 1.5,
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      pointHitRadius: 8,
    }],
  }), [normalized.labels, normalized.values, lineColor]);

  const options = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        enabled: true,
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (ctx) => new Intl.NumberFormat('ko-KR').format(ctx.raw) + '원',
        },
      },
    },
    scales: {
      x: { display: false },
      y: { display: false },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
  }), []);

  if (!normalized.values.length) return null;

  return (
    <div className="w-full" style={{ height }}>
      <Line data={data} options={options} />
    </div>
  );
}
