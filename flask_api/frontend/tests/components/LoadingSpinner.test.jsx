import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../../src/components/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render spinner container', () => {
    render(<LoadingSpinner />);
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should render spinner element', () => {
    render(<LoadingSpinner />);
    const container = screen.getByTestId('loading-spinner');
    expect(container.querySelector('.spinner')).toBeInTheDocument();
  });

  it('should apply medium size class by default', () => {
    render(<LoadingSpinner />);
    const container = screen.getByTestId('loading-spinner');
    expect(container.classList.contains('spinner-small')).toBe(false);
  });

  it('should apply small size class when size is small', () => {
    render(<LoadingSpinner size="small" />);
    const container = screen.getByTestId('loading-spinner');
    expect(container.classList.contains('spinner-small')).toBe(true);
  });

  it('should not apply small class for medium size', () => {
    render(<LoadingSpinner size="medium" />);
    const container = screen.getByTestId('loading-spinner');
    expect(container.classList.contains('spinner-small')).toBe(false);
  });

  it('should always include spinner-container class', () => {
    render(<LoadingSpinner />);
    const container = screen.getByTestId('loading-spinner');
    expect(container.classList.contains('spinner-container')).toBe(true);
  });
});
