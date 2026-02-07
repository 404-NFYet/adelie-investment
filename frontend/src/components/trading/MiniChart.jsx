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

export default function MiniChart({ dates = [], values = [], color = '#4F46E5', height = 80 }) {
  const isPositive = values.length >= 2 && values[values.length - 1] >= values[0];
  const lineColor = color === 'auto' ? (isPositive ? '#EF4444' : '#3B82F6') : color;

  const data = useMemo(() => ({
    labels: dates,
    datasets: [{
      data: values,
      borderColor: lineColor,
      backgroundColor: lineColor + '20',
      borderWidth: 1.5,
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      pointHitRadius: 8,
    }],
  }), [dates, values, lineColor]);

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

  if (!values.length) return null;

  return (
    <div style={{ height }}>
      <Line data={data} options={options} />
    </div>
  );
}
