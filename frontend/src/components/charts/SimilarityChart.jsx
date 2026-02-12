/**
 * SimilarityChart.jsx - 유사도 비교 막대 차트 (Chart.js)
 */
import { useRef, useEffect } from 'react';

export default function SimilarityChart({ score = 75, label = '유사도', className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    let Chart;
    const loadChart = async () => {
      const module = await import('chart.js/auto');
      Chart = module.default;

      if (chartRef.current) {
        chartRef.current.destroy();
      }

      if (!canvasRef.current) return;

      chartRef.current = new Chart(canvasRef.current, {
        type: 'bar',
        data: {
          labels: [label],
          datasets: [{
            data: [score],
            backgroundColor: score >= 70 ? '#FF6B00' : score >= 50 ? '#3B82F6' : '#6B7280',
            borderRadius: 8,
            barThickness: 40,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.parsed.x}%`,
              },
            },
          },
          scales: {
            x: {
              min: 0,
              max: 100,
              grid: { display: false },
              ticks: {
                callback: (val) => `${val}%`,
                font: { size: 10 },
              },
            },
            y: {
              grid: { display: false },
              ticks: { font: { size: 12 } },
            },
          },
          animation: {
            duration: 1500,
            easing: 'easeOutQuart',
          },
        },
      });
    };

    loadChart();

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [score, label]);

  return (
    <div className={`h-16 ${className}`}>
      <canvas ref={canvasRef} />
    </div>
  );
}
