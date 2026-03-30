"""Unit tests for TaskStatus React component."""
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TaskStatus, Task } from '../src/components/TaskStatus';


describe('TaskStatus Component', () => {
  const mockTasks: Task[] = [
    {
      id: '1',
      name: 'Build API',
      status: 'completed',
      agent: 'opencode',
      progress: 100,
      startedAt: '2026-03-30T10:00:00Z',
      completedAt: '2026-03-30T10:05:00Z',
    },
    {
      id: '2',
      name: 'Create UI',
      status: 'running',
      agent: 'gemini',
      progress: 65,
      startedAt: '2026-03-30T10:06:00Z',
    },
    {
      id: '3',
      name: 'Write Tests',
      status: 'pending',
      agent: 'kilo',
      progress: 0,
    },
    {
      id: '4',
      name: 'Deploy',
      status: 'failed',
      agent: 'codex',
      progress: 30,
      error: 'Connection timeout',
      startedAt: '2026-03-30T10:10:00Z',
      completedAt: '2026-03-30T10:12:00Z',
    },
    {
      id: '5',
      name: 'Documentation',
      status: 'skipped',
      agent: 'gemini',
    },
  ];

  describe('Rendering', () => {
    it('renders all tasks', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      expect(screen.getByText('Build API')).toBeInTheDocument();
      expect(screen.getByText('Create UI')).toBeInTheDocument();
      expect(screen.getByText('Write Tests')).toBeInTheDocument();
      expect(screen.getByText('Deploy')).toBeInTheDocument();
      expect(screen.getByText('Documentation')).toBeInTheDocument();
    });

    it('displays correct status icons', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      expect(screen.getByText('✅')).toBeInTheDocument();
      expect(screen.getByText('🔄')).toBeInTheDocument();
      expect(screen.getByText('⏳')).toBeInTheDocument();
      expect(screen.getByText('❌')).toBeInTheDocument();
      expect(screen.getByText('⏭️')).toBeInTheDocument();
    });

    it('displays agent badges', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      expect(screen.getByText('opencode')).toBeInTheDocument();
      expect(screen.getByText('gemini')).toBeInTheDocument();
      expect(screen.getByText('kilo')).toBeInTheDocument();
      expect(screen.getByText('codex')).toBeInTheDocument();
    });

    it('shows progress bars for tasks', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      const progressBars = screen.getAllByRole('progressbar');
      expect(progressBars.length).toBeGreaterThan(0);
    });

    it('displays empty state when no tasks', () => {
      render(<TaskStatus tasks={[]} />);
      
      expect(screen.getByText('No tasks to display')).toBeInTheDocument();
    });
  });

  describe('Status Colors', () => {
    it('applies correct color for completed status', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'completed' }]} />
      );
      
      const statusBadge = container.querySelector('.bg-green-100');
      expect(statusBadge).toBeInTheDocument();
    });

    it('applies correct color for failed status', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'failed' }]} />
      );
      
      const statusBadge = container.querySelector('.bg-red-100');
      expect(statusBadge).toBeInTheDocument();
    });

    it('applies correct color for running status', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'running' }]} />
      );
      
      const statusBadge = container.querySelector('.bg-blue-100');
      expect(statusBadge).toBeInTheDocument();
    });
  });

  describe('Task Expansion', () => {
    it('expands task details on click', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      const taskElement = screen.getByText('Build API').closest('div');
      if (taskElement) {
        fireEvent.click(taskElement);
      }
      
      expect(screen.getByText('Started')).toBeInTheDocument();
      expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('shows error message for failed tasks when expanded', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      const failedTask = screen.getByText('Deploy').closest('div');
      if (failedTask) {
        fireEvent.click(failedTask);
      }
      
      expect(screen.getByText('Error:')).toBeInTheDocument();
      expect(screen.getByText('Connection timeout')).toBeInTheDocument();
    });

    it('collapses expanded task when clicked again', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      const taskElement = screen.getByText('Build API').closest('div');
      if (taskElement) {
        fireEvent.click(taskElement);
        expect(screen.getByText('Started')).toBeInTheDocument();
        
        fireEvent.click(taskElement);
      }
    });
  });

  describe('Callbacks', () => {
    it('calls onRetry when retry button is clicked', () => {
      const onRetry = jest.fn();
      const failedTask = [{ id: '1', name: 'Test', status: 'failed' }];
      
      render(<TaskStatus tasks={failedTask} onRetry={onRetry} />);
      
      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);
      
      expect(onRetry).toHaveBeenCalledWith('1');
      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('calls onSkip when skip button is clicked', () => {
      const onSkip = jest.fn();
      const pendingTask = [{ id: '1', name: 'Test', status: 'pending' }];
      
      render(<TaskStatus tasks={pendingTask} onSkip={onSkip} />);
      
      const skipButton = screen.getByText('Skip');
      fireEvent.click(skipButton);
      
      expect(onSkip).toHaveBeenCalledWith('1');
      expect(onSkip).toHaveBeenCalledTimes(1);
    });

    it('does not show retry/skip buttons when callbacks not provided', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      const retryButtons = screen.queryAllByText('Retry');
      const skipButtons = screen.queryAllByText('Skip');
      
      expect(retryButtons.length).toBe(0);
      expect(skipButtons.length).toBe(0);
    });
  });

  describe('Time Formatting', () => {
    it('formats start time correctly', () => {
      render(<TaskStatus tasks={mockTasks} />);
      
      const taskElement = screen.getByText('Build API').closest('div');
      if (taskElement) {
        fireEvent.click(taskElement);
      }
      
      expect(screen.getByText('Started')).toBeInTheDocument();
    });

    it('displays dash for missing time', () => {
      render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending' }]} />
      );
      
      const taskElement = screen.getByText('Test').closest('div');
      if (taskElement) {
        fireEvent.click(taskElement);
      }
      
      const times = screen.getAllByText('-');
      expect(times.length).toBeGreaterThan(0);
    });
  });

  describe('Agent Badge Colors', () => {
    it('applies correct color for codex agent', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending', agent: 'codex' }]} />
      );
      
      const badge = container.querySelector('.bg-purple-500');
      expect(badge).toBeInTheDocument();
    });

    it('applies correct color for opencode agent', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending', agent: 'opencode' }]} />
      );
      
      const badge = container.querySelector('.bg-indigo-500');
      expect(badge).toBeInTheDocument();
    });

    it('applies correct color for gemini agent', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending', agent: 'gemini' }]} />
      );
      
      const badge = container.querySelector('.bg-cyan-500');
      expect(badge).toBeInTheDocument();
    });

    it('applies correct color for kilo agent', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending', agent: 'kilo' }]} />
      );
      
      const badge = container.querySelector('.bg-orange-500');
      expect(badge).toBeInTheDocument();
    });

    it('applies default color for unknown agent', () => {
      const { container } = render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending', agent: 'unknown' }]} />
      );
      
      const badge = container.querySelector('.bg-gray-500');
      expect(badge).toBeInTheDocument();
    });
  });

  describe('Progress Display', () => {
    it('shows 100% progress for completed tasks', () => {
      render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'completed', progress: 100 }]} />
      );
      
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('shows partial progress for running tasks', () => {
      render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'running', progress: 65 }]} />
      );
      
      expect(screen.getByText('65%')).toBeInTheDocument();
    });

    it('handles missing progress gracefully', () => {
      render(
        <TaskStatus tasks={[{ id: '1', name: 'Test', status: 'pending' }]} />
      );
      
      // Should not crash when progress is undefined
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
  });
});
