import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingOverlay } from '../../src/components/LoadingOverlay';

describe('LoadingOverlay', () => {
  it('should not render when not loading', () => {
    render(<LoadingOverlay isLoading={false} />);
    expect(screen.queryByTestId('loading-overlay')).not.toBeInTheDocument();
  });

  it('should render when loading', () => {
    render(<LoadingOverlay isLoading={true} />);
    expect(screen.getByTestId('loading-overlay')).toBeInTheDocument();
  });

  it('should display loading message', () => {
    render(<LoadingOverlay isLoading={true} />);
    expect(screen.getByText('Loading analytics...')).toBeInTheDocument();
  });
});
