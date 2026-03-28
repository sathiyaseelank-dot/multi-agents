import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChartCard } from '../../src/components/ChartCard';

describe('ChartCard', () => {
  it('should render chart title', () => {
    render(
      <ChartCard title="Messages Over Time">
        <canvas />
      </ChartCard>
    );
    expect(screen.getByText('Messages Over Time')).toBeInTheDocument();
  });

  it('should render children content', () => {
    render(
      <ChartCard title="Test Chart">
        <canvas data-testid="chart-canvas" />
      </ChartCard>
    );
    expect(screen.getByTestId('chart-canvas')).toBeInTheDocument();
  });

  it('should render empty state when children is null', () => {
    render(<ChartCard title="Test Chart">{null}</ChartCard>);
    expect(screen.getByText('No chart data available')).toBeInTheDocument();
  });

  it('should render empty state when children is undefined', () => {
    render(<ChartCard title="Test Chart">{undefined}</ChartCard>);
    expect(screen.getByText('No chart data available')).toBeInTheDocument();
  });

  it('should apply wide class when isWide is true', () => {
    const { container } = render(
      <ChartCard title="Distribution" isWide={true}>
        <canvas />
      </ChartCard>
    );
    expect(container.querySelector('.chart-wide')).toBeInTheDocument();
  });

  it('should not apply wide class when isWide is false', () => {
    const { container } = render(
      <ChartCard title="Messages" isWide={false}>
        <canvas />
      </ChartCard>
    );
    expect(container.querySelector('.chart-wide')).not.toBeInTheDocument();
  });

  it('should render days filter when showDaysFilter is true', () => {
    render(
      <ChartCard
        title="Messages"
        showDaysFilter={true}
        daysOptions={[7, 14, 30]}
        selectedDays={7}
      >
        <canvas />
      </ChartCard>
    );
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('should not render days filter when showDaysFilter is false', () => {
    render(
      <ChartCard title="Messages" showDaysFilter={false}>
        <canvas />
      </ChartCard>
    );
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('should render all day options in filter', () => {
    render(
      <ChartCard
        title="Messages"
        showDaysFilter={true}
        daysOptions={[7, 14, 30]}
        selectedDays={7}
      >
        <canvas />
      </ChartCard>
    );
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(3);
    expect(options[0]).toHaveTextContent('7 days');
    expect(options[1]).toHaveTextContent('14 days');
    expect(options[2]).toHaveTextContent('30 days');
  });

  it('should reflect selectedDays value in filter', () => {
    render(
      <ChartCard
        title="Messages"
        showDaysFilter={true}
        daysOptions={[7, 14, 30]}
        selectedDays={30}
      >
        <canvas />
      </ChartCard>
    );
    expect(screen.getByRole('combobox')).toHaveValue('30');
  });

  it('should call onDaysChange when filter value changes', async () => {
    const onDaysChange = vi.fn();
    const user = userEvent.setup();

    render(
      <ChartCard
        title="Messages"
        showDaysFilter={true}
        daysOptions={[7, 14, 30]}
        selectedDays={7}
        onDaysChange={onDaysChange}
      >
        <canvas />
      </ChartCard>
    );

    await user.selectOptions(screen.getByRole('combobox'), '30');
    expect(onDaysChange).toHaveBeenCalledWith(30);
  });

  it('should render chart container div', () => {
    const { container } = render(
      <ChartCard title="Test">
        <canvas />
      </ChartCard>
    );
    expect(container.querySelector('.chart-container')).toBeInTheDocument();
  });
});
