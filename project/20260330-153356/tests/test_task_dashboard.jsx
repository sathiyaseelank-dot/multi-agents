"""Unit and integration tests for TaskDashboard component."""
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import TaskDashboard from '../src/components/TaskDashboard';


// Mock the fetch API
global.fetch = jest.fn();

describe('TaskDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Loading State', () => {
    test('displays loading message initially', () => {
      // Mock fetch to never resolve (simulating loading)
      global.fetch.mockImplementation(() => new Promise(() => {}));

      render(<TaskDashboard />);

      expect(screen.getByText('Loading tasks...')).toBeInTheDocument();
      expect(screen.getByText('Loading tasks...')).toHaveClass('loading');
    });
  });

  describe('Error State', () => {
    test('displays error message when fetch fails', async () => {
      const errorMessage = 'Network error';
      global.fetch.mockRejectedValue(new Error(errorMessage));

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
      });
    });

    test('displays error when response is not ok', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Error: Failed to fetch tasks')).toBeInTheDocument();
      });
    });
  });

  describe('Empty State', () => {
    test('displays no tasks message when tasks array is empty', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(screen.getByText('No tasks found')).toBeInTheDocument();
      });

      expect(screen.queryByRole('list')).not.toBeInTheDocument();
    });
  });

  describe('Success State', () => {
    const mockTasks = [
      {
        session_id: '20260330-120000',
        status: 'COMPLETED',
        task_description: 'Build a REST API with user authentication',
        created_at: '2026-03-30 12:00:00',
        task_count: 5,
      },
      {
        session_id: '20260330-130000',
        status: 'FAILED',
        task_description: 'Create a todo application',
        created_at: '2026-03-30 13:00:00',
        task_count: 3,
      },
      {
        session_id: '20260330-140000',
        status: 'EXECUTING',
        task_description: 'Build a chat interface',
        created_at: '2026-03-30 14:00:00',
        task_count: 4,
      },
    ];

    test('displays tasks when fetch is successful', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockTasks,
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Task Dashboard')).toBeInTheDocument();
      });

      // Check task cards are rendered
      expect(screen.getAllByRole('article')).toHaveLength(3);

      // Check task content
      expect(screen.getByText('20260330-120000')).toBeInTheDocument();
      expect(screen.getByText('COMPLETED')).toBeInTheDocument();
      expect(screen.getByText('Build a REST API with user authentication')).toBeInTheDocument();
    });

    test('displays correct status colors', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockTasks,
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        const completedStatus = screen.getByText('COMPLETED');
        expect(completedStatus).toHaveStyle('background-color: #22c55e');
      });

      await waitFor(() => {
        const failedStatus = screen.getByText('FAILED');
        expect(failedStatus).toHaveStyle('background-color: #ef4444');
      });

      await waitFor(() => {
        const executingStatus = screen.getByText('EXECUTING');
        expect(executingStatus).toHaveStyle('background-color: #3b82f6');
      });
    });

    test('displays task metadata', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockTasks,
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(screen.getByText('Created: 2026-03-30 12:00:00')).toBeInTheDocument();
        expect(screen.getByText('Tasks: 5')).toBeInTheDocument();
      });
    });
  });

  describe('Status Color Mapping', () => {
    const statusColors = {
      COMPLETED: '#22c55e',
      FAILED: '#ef4444',
      EXECUTING: '#3b82f6',
      PLANNING: '#f59e0b',
      VALIDATING: '#8b5cf6',
      RUNNING: '#06b6d4',
    };

    test.each(Object.entries(statusColors))(
      'maps %s status to color %s',
      async (status, color) => {
        const task = {
          session_id: 'test-123',
          status: status,
          task_description: 'Test task',
          created_at: '2026-03-30',
          task_count: 1,
        };

        global.fetch.mockResolvedValue({
          ok: true,
          json: async () => [task],
        });

        render(<TaskDashboard />);

        await waitFor(() => {
          const statusElement = screen.getByText(status);
          expect(statusElement).toHaveStyle(`background-color: ${color}`);
        });
      }
    );

    test('uses default color for unknown status', async () => {
      const task = {
        session_id: 'test-123',
        status: 'UNKNOWN_STATUS',
        task_description: 'Test task',
        created_at: '2026-03-30',
        task_count: 1,
      };

      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => [task],
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        const statusElement = screen.getByText('UNKNOWN_STATUS');
        expect(statusElement).toHaveStyle('background-color: #6b7280');
      });
    });
  });

  describe('API Integration', () => {
    test('fetches from correct endpoint', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith('/api/orchestrator/sessions');
      });
    });

    test('fetches only once on mount', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Accessibility', () => {
    test('has proper heading structure', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => [],
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Task Dashboard');
      });
    });

    test('task cards are identifiable', async () => {
      const mockTasks = [
        {
          session_id: 'test-123',
          status: 'COMPLETED',
          task_description: 'Test task',
          created_at: '2026-03-30',
          task_count: 1,
        },
      ];

      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => mockTasks,
      });

      render(<TaskDashboard />);

      await waitFor(() => {
        const taskCards = document.querySelectorAll('.task-card');
        expect(taskCards).toHaveLength(1);
      });
    });
  });
});
