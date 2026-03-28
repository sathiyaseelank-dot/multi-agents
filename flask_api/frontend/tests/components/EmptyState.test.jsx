import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmptyState } from '../../src/components/EmptyState';

describe('EmptyState', () => {
  it('should render default title', () => {
    render(<EmptyState message="No data" />);
    expect(screen.getByText('No Data')).toBeInTheDocument();
  });

  it('should render custom title', () => {
    render(<EmptyState title="Custom Title" message="No data" />);
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('should render message', () => {
    render(<EmptyState message="Custom message" />);
    expect(screen.getByText('Custom message')).toBeInTheDocument();
  });

  it('should render retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<EmptyState onRetry={onRetry} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('should not render retry button when onRetry is not provided', () => {
    render(<EmptyState />);
    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('should call onRetry when retry button is clicked', () => {
    const onRetry = vi.fn();
    render(<EmptyState onRetry={onRetry} />);
    screen.getByText('Retry').click();
    expect(onRetry).toHaveBeenCalled();
  });
});
