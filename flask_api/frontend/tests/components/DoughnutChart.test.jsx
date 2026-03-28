import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Chart } from 'chart.js';
import { DoughnutChart } from '../../src/components/DoughnutChart';

vi.mock('chart.js', () => {
  const mockInstance = { destroy: vi.fn() };
  const ChartMock = vi.fn(() => mockInstance);
  ChartMock.register = vi.fn();
  return {
    Chart: ChartMock,
    registerables: [],
  };
});

describe('DoughnutChart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading spinner when isLoading is true', () => {
    render(<DoughnutChart data={[]} isLoading={true} />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should not render spinner when not loading', () => {
    const data = [{ label: 'Text', value: 50 }];
    render(<DoughnutChart data={data} isLoading={false} />);
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });

  it('should render canvas element when data is provided', () => {
    const data = [{ label: 'Text', value: 50 }];
    const { container } = render(<DoughnutChart data={data} />);
    expect(container.querySelector('canvas')).toBeInTheDocument();
  });

  it('should not create chart when data is empty', () => {
    render(<DoughnutChart data={[]} />);
    expect(Chart).not.toHaveBeenCalled();
  });

  it('should not create chart when data is null', () => {
    render(<DoughnutChart data={null} />);
    expect(Chart).not.toHaveBeenCalled();
  });

  it('should create a doughnut chart with correct type', () => {
    const data = [{ label: 'Text', value: 50 }];
    render(<DoughnutChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ type: 'doughnut' })
    );
  });

  it('should pass correct labels and values to chart', () => {
    const data = [
      { label: 'Text', value: 60 },
      { label: 'Image', value: 30 },
      { label: 'Video', value: 10 },
    ];
    render(<DoughnutChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        data: expect.objectContaining({
          labels: ['Text', 'Image', 'Video'],
          datasets: [
            expect.objectContaining({
              data: [60, 30, 10],
            }),
          ],
        }),
      })
    );
  });

  it('should apply background colors to dataset', () => {
    const data = [
      { label: 'A', value: 40 },
      { label: 'B', value: 60 },
    ];
    render(<DoughnutChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        data: expect.objectContaining({
          datasets: [
            expect.objectContaining({
              backgroundColor: expect.arrayContaining([expect.any(String)]),
            }),
          ],
        }),
      })
    );
  });

  it('should destroy previous chart when data changes', () => {
    const mockDestroy = vi.fn();
    Chart.mockReturnValueOnce({ destroy: mockDestroy });

    const data1 = [{ label: 'A', value: 50 }];
    const { rerender } = render(<DoughnutChart data={data1} />);

    const data2 = [{ label: 'B', value: 80 }];
    rerender(<DoughnutChart data={data2} />);

    expect(mockDestroy).toHaveBeenCalled();
  });

  it('should configure legend position to the right', () => {
    const data = [{ label: 'Text', value: 50 }];
    render(<DoughnutChart data={data} />);
    expect(Chart).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        options: expect.objectContaining({
          plugins: expect.objectContaining({
            legend: expect.objectContaining({ position: 'right' }),
          }),
        }),
      })
    );
  });
});
