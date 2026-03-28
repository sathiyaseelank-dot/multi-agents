import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TopLists } from '../../src/components/TopLists';
import { useAnalyticsStore } from '../../src/stores/analyticsStore';

vi.mock('../../src/stores/analyticsStore', () => ({
  useAnalyticsStore: vi.fn(),
}));

describe('TopLists', () => {
  const mockTopUsers = [
    { id: 1, username: 'user1', email: 'user1@test.com', message_count: 50, last_activity: '2024-01-15' },
    { id: 2, username: 'user2', email: 'user2@test.com', message_count: 30, last_activity: '2024-01-14' },
  ];

  const mockTopConversations = [
    { id: 1, name: 'Conversation 1', is_group: true, participant_count: 5, message_count: 100 },
    { id: 2, name: 'Conversation 2', is_group: false, participant_count: 2, message_count: 50 },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render top users table', () => {
    useAnalyticsStore.mockReturnValue({
      isLoading: { topUsers: false, topConversations: false },
    });

    render(<TopLists topUsers={mockTopUsers} topConversations={[]} />);
    
    expect(screen.getByText('Top Active Users')).toBeInTheDocument();
    expect(screen.getByText('user1')).toBeInTheDocument();
  });

  it('should render top conversations table', () => {
    useAnalyticsStore.mockReturnValue({
      isLoading: { topUsers: false, topConversations: false },
    });

    render(<TopLists topUsers={[]} topConversations={mockTopConversations} />);
    
    expect(screen.getByText('Top Conversations')).toBeInTheDocument();
    expect(screen.getByText('Conversation 1')).toBeInTheDocument();
  });

  it('should show loading state for top users', () => {
    useAnalyticsStore.mockReturnValue({
      isLoading: { topUsers: true, topConversations: false },
    });

    render(<TopLists topUsers={[]} topConversations={[]} />);
    
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should show empty state when no users', () => {
    useAnalyticsStore.mockReturnValue({
      isLoading: { topUsers: false, topConversations: false },
    });

    render(<TopLists topUsers={[]} topConversations={[]} />);
    
    expect(screen.getByText('No user data available')).toBeInTheDocument();
    expect(screen.getByText('No conversation data available')).toBeInTheDocument();
  });

  it('should display user message counts', () => {
    useAnalyticsStore.mockReturnValue({
      isLoading: { topUsers: false, topConversations: false },
    });

    render(<TopLists topUsers={mockTopUsers} topConversations={[]} />);
    
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
  });

  it('should display conversation type correctly', () => {
    useAnalyticsStore.mockReturnValue({
      isLoading: { topUsers: false, topConversations: false },
    });

    render(<TopLists topUsers={[]} topConversations={mockTopConversations} />);
    
    expect(screen.getByText('Group')).toBeInTheDocument();
    expect(screen.getByText('Direct')).toBeInTheDocument();
  });
});
