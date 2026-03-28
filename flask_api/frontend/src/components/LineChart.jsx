import { useRef, useEffect } from 'react';
import { Chart, registerables } from 'chart.js';
import { LoadingSpinner } from './LoadingSpinner';

Chart.register(...registerables);

export function LineChart({ data, isLoading }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data || data.length === 0) return;

    const ctx = canvasRef.current.getContext('2d');

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.map((d) => d.label),
        datasets: [
          {
            label: 'Count',
            data: data.map((d) => d.value),
            borderColor: '#4a90d9',
            backgroundColor: 'rgba(74, 144, 217, 0.1)',
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: { grid: { display: false } },
          y: { 
            beginAtZero: true, 
            grid: { color: '#f0f0f0' },
            ticks: { precision: 0 }
          },
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
