import { useRef, useEffect } from 'react';
import { Chart, registerables } from 'chart.js';
import { LoadingSpinner } from './LoadingSpinner';

Chart.register(...registerables);

const COLORS = ['#4a90d9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

export function DoughnutChart({ data, isLoading }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const ctx = canvasRef.current.getContext('2d');

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    chartRef.current = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map((d) => d.label),
        datasets: [
          {
            label: 'Count',
            data: data.map((d) => d.value),
            backgroundColor: COLORS.slice(0, data.length),
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' },
        },
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [data]);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return <canvas ref={canvasRef} />;
}
