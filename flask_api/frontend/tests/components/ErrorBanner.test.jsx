import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorBanner } from '../../src/components/ErrorBanner';

describe('ErrorBanner', () => {
  it('should not render when no error', () => {
    render(<ErrorBanner error={null} />);
    expect(screen.queryByTestId('error-banner')).not.toBeInTheDocument();
  });

  it('should render error message', () => {
    render(<ErrorBanner error={{ message: 'Test error' }} />);
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });

  it('should render default message when error has no message', () => {
    render(<ErrorBanner error={{}} />);
    expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
  });

  it('should render retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<ErrorBanner error={{ message: 'Error' }} onRetry={onRetry} />);
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('should render dismiss button when onDismiss is provided', () => {
    const onDismiss = vi.fn();
    render(<ErrorBanner error={{ message: 'Error' }} onDismiss={onDismiss} />);
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
  });

  it('should call onRetry when retry button is clicked', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorBanner error={{ message: 'Error' }} onRetry={onRetry} />);
    await user.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('should call onDismiss when dismiss button is clicked', async () => {
    const onDismiss = vi.fn();
    const user = userEvent.setup();
    render(<ErrorBanner error={{ message: 'Error' }} onDismiss={onDismiss} />);
    await user.click(screen.getByText('Dismiss'));
    expect(onDismiss).toHaveBeenCalled();
  });
});
