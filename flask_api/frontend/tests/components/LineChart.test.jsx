import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Chart } from 'chart.js';
import { LineChart } from '../../src/components/LineChart';

vi.mock('chart.js', () => {
  const mockInstance = { destroy: vi.fn() };
  const ChartMock = vi.fn(() => mockInstance);
  ChartMock.register = vi.fn();
  return {
    Chart: ChartMock,
    registerables: [],
  };
});

describe('LineChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading spinner when isLoading is true', () => {
    render(<LineChart data={[]} isLoading={true} />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should not render spinner when not loading', () => {
    const data = [{ label: 'Day 1', value: 10 }];
    render(<LineChart data={data} isLoading={false} />);
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });

  it('should render canvas element when data is provided', () => {
    const data = [{ label: 'Day 1', value: 10 }];
    const { container } = render(<LineChart data={data} />);
    expect(container.querySelector('canvas')).toBeInTheDocument();
  });

  it('should not create chart when data is empty', () => {
    render(<LineChart data={[]} />);
    expect(Chart).not.toHaveBeenCalled();
  });

  it('should not create chart when data is null', () => {
    render(<LineChart data={null} />);
    expect(Chart).not.toHaveBeenCalled();
  });

  it('should create a line chart with correct type', () => {
    const data = [
      { label: 'Day 1', value: 10 },
      { label: 'Day 2', value: 20 },
    ];
    render(<LineChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: 'line' })
    );
  });

  it('should pass correct labels and data to chart', () => {
    const data = [
      { label: 'Mon', value: 5 },
      { label: 'Tue', value: 15 },
      { label: 'Wed', value: 25 },
    ];
    render(<LineChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        data: expect.objectContaining({
          labels: ['Mon', 'Tue', 'Wed'],
          datasets: [
            expect.objectContaining({
              data: [5, 15, 25],
            }),
          ],
        }),
      })
    );
  });

  it('should destroy previous chart when data changes', () => {
    const mockDestroy = vi.fn();
    Chart.mockReturnValueOnce({ destroy: mockDestroy });

    const data1 = [{ label: 'Day 1', value: 10 }];
    const { rerender } = render(<LineChart data={data1} />);

    const data2 = [{ label: 'Day 2', value: 20 }];
    rerender(<LineChart data={data2} />);

    expect(mockDestroy).toHaveBeenCalled();
  });

  it('should configure fill and tension for line chart', () => {
    const data = [{ label: 'Day 1', value: 10 }];
    render(<LineChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        data: expect.objectContaining({
          datasets: [
            expect.objectContaining({
              fill: true,
              tension: 0.4,
            }),
          ],
        }),
      })
    );
  });

  it('should set responsive and maintainAspectRatio options', () => {
    const data = [{ label: 'Day 1', value: 10 }];
    render(<LineChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        options: expect.objectContaining({
          responsive: true,
          maintainAspectRatio: false,
        }),
      })
    );
  });
});
