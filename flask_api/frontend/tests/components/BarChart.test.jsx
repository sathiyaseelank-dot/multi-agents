import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Chart } from 'chart.js';
import { BarChart } from '../../src/components/BarChart';

vi.mock('chart.js', () => {
  const mockInstance = { destroy: vi.fn() };
  const ChartMock = vi.fn(() => mockInstance);
  ChartMock.register = vi.fn();
  return {
    Chart: ChartMock,
    registerables: [],
  };
});

describe('BarChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading spinner when isLoading is true', () => {
    render(<BarChart data={[]} isLoading={true} />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should not render spinner when not loading', () => {
    const data = [{ label: 'Hour 0', value: 5 }];
    render(<BarChart data={data} isLoading={false} />);
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });

  it('should render canvas element when data is provided', () => {
    const data = [{ label: 'Hour 0', value: 5 }];
    const { container } = render(<BarChart data={data} />);
    expect(container.querySelector('canvas')).toBeInTheDocument();
  });

  it('should not create chart when data is empty', () => {
    render(<BarChart data={[]} />);
    expect(Chart).not.toHaveBeenCalled();
  });

  it('should not create chart when data is null', () => {
    render(<BarChart data={null} />);
    expect(Chart).not.toHaveBeenCalled();
  });

  it('should create a bar chart with correct type', () => {
    const data = [{ label: 'Hour 0', value: 5 }];
    render(<BarChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: 'bar' })
    );
  });

  it('should pass correct labels and values to chart', () => {
    const data = [
      { label: '00:00', value: 10 },
      { label: '01:00', value: 25 },
      { label: '02:00', value: 15 },
    ];
    render(<BarChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        data: expect.objectContaining({
          labels: ['00:00', '01:00', '02:00'],
          datasets: [
            expect.objectContaining({
              data: [10, 25, 15],
            }),
          ],
        }),
      })
    );
  });

  it('should destroy previous chart when data changes', () => {
    const mockDestroy = vi.fn();
    Chart.mockReturnValueOnce({ destroy: mockDestroy });

    const data1 = [{ label: 'Hour 0', value: 5 }];
    const { rerender } = render(<BarChart data={data1} />);

    const data2 = [{ label: 'Hour 1', value: 10 }];
    rerender(<BarChart data={data2} />);

    expect(mockDestroy).toHaveBeenCalled();
  });

  it('should configure bar chart scales correctly', () => {
    const data = [{ label: 'Hour 0', value: 5 }];
    render(<BarChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        options: expect.objectContaining({
          responsive: true,
          maintainAspectRatio: false,
          scales: expect.objectContaining({
            x: expect.objectContaining({
              grid: expect.objectContaining({ display: false }),
            }),
            y: expect.objectContaining({
              beginAtZero: true,
              ticks: expect.objectContaining({ precision: 0 }),
            }),
          }),
        }),
      })
    );
  });
});
