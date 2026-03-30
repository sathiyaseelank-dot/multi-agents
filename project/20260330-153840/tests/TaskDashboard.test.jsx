/**
 * Unit tests for TaskDashboard React component
 * Run with: npm test -- TaskDashboard.test.jsx
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import TaskDashboard from '../src/TaskDashboard';

// Mock data
const mockTasks = [
  {
    id: 'task-001',
    name: 'Initialize Project',
    description: 'Set up project structure',
    status: 'completed',
    agent: 'opencode',
    duration: 12.5,
    output: 'Project initialized successfully'
  },
  {
    id: 'task-002',
    name: 'Create Database Schema',
    description: 'Design database models',
    status: 'in_progress',
    agent: 'opencode',
    duration: 8.3
  },
  {
    id: 'task-003',
    name: 'Build Login Component',
    description: 'Create React login form',
    status: 'pending',
    agent: 'gemini'
  },
  {
    id: 'task-004',
    name: 'Write Unit Tests',
    description: 'Add test coverage',
    status: 'pending',
    agent: 'kilo'
  },
  {
    id: 'task-005',
    name: 'Setup CI/CD Pipeline',
    description: 'Configure automated testing',
    status: 'failed',
    agent: 'opencode',
    error: 'Configuration file not found'
  }
];

describe('TaskDashboard', () => {
  describe('Rendering', () => {
    test('renders dashboard with tasks', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      expect(screen.getByText('Task Dashboard')).toBeInTheDocument();
      expect(screen.getByText(/Initialize Project/i)).toBeInTheDocument();
      expect(screen.getByText(/Create Database Schema/i)).toBeInTheDocument();
    });

    test('renders with empty tasks array', () => {
      render(<TaskDashboard tasks={[]} />);
      
      expect(screen.getByText('Task Dashboard')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument(); // Total count
    });

    test('renders dashboard stats', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      expect(screen.getByText('5')).toBeInTheDocument(); // Total
      expect(screen.getByText('1')).toBeInTheDocument(); // Completed
      expect(screen.getByText('1')).toBeInTheDocument(); // In Progress
      expect(screen.getByText('1')).toBeInTheDocument(); // Failed
    });
  });

  describe('Statistics', () => {
    test('calculates correct statistics', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const statItems = screen.getAllByTestId(/stat-/i);
      expect(statItems).toHaveLength(4); // total, completed, in-progress, failed
    });

    test('displays progress bar with correct percentage', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      // 1 completed out of 5 = 20%
      const progressText = screen.getByText(/20%/i);
      expect(progressText).toBeInTheDocument();
    });

    test('updates stats when tasks change', () => {
      const { rerender } = render(<TaskDashboard tasks={mockTasks} />);
      
      expect(screen.getByText('1')).toBeInTheDocument(); // 1 completed
      
      const newTasks = [
        ...mockTasks,
        {
          id: 'task-006',
          name: 'New Task',
          status: 'completed',
          agent: 'opencode'
        }
      ];
      
      rerender(<TaskDashboard tasks={newTasks} />);
      
      expect(screen.getByText('2')).toBeInTheDocument(); // 2 completed now
    });
  });

  describe('Filtering', () => {
    test('filters tasks by status', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      // Click "Pending" filter
      const pendingBtn = screen.getByRole('button', { name: /pending/i });
      fireEvent.click(pendingBtn);
      
      // Should only show pending tasks
      expect(screen.getByText(/Build Login Component/i)).toBeInTheDocument();
      expect(screen.getByText(/Write Unit Tests/i)).toBeInTheDocument();
    });

    test('filters tasks by completed status', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const completedBtn = screen.getByRole('button', { name: /completed/i });
      fireEvent.click(completedBtn);
      
      expect(screen.getByText(/Initialize Project/i)).toBeInTheDocument();
      expect(screen.queryByText(/Build Login Component/i)).not.toBeInTheDocument();
    });

    test('filters tasks by in_progress status', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const inProgressBtn = screen.getByRole('button', { name: /in progress/i });
      fireEvent.click(inProgressBtn);
      
      expect(screen.getByText(/Create Database Schema/i)).toBeInTheDocument();
    });

    test('filters tasks by failed status', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const failedBtn = screen.getByRole('button', { name: /failed/i });
      fireEvent.click(failedBtn);
      
      expect(screen.getByText(/Setup CI\/CD Pipeline/i)).toBeInTheDocument();
    });

    test('shows all tasks when "All" filter is selected', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const allBtn = screen.getByRole('button', { name: /all/i });
      fireEvent.click(allBtn);
      
      expect(screen.getByText(/Initialize Project/i)).toBeInTheDocument();
      expect(screen.getByText(/Create Database Schema/i)).toBeInTheDocument();
      expect(screen.getByText(/Build Login Component/i)).toBeInTheDocument();
    });
  });

  describe('Search', () => {
    test('searches by task name', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const searchInput = screen.getByPlaceholderText(/search tasks/i);
      fireEvent.change(searchInput, { target: { value: 'login' } });
      
      expect(screen.getByText(/Build Login Component/i)).toBeInTheDocument();
      expect(screen.queryByText(/Initialize Project/i)).not.toBeInTheDocument();
    });

    test('searches by task ID', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const searchInput = screen.getByPlaceholderText(/search tasks/i);
      fireEvent.change(searchInput, { target: { value: 'task-001' } });
      
      expect(screen.getByText(/Initialize Project/i)).toBeInTheDocument();
      expect(screen.queryByText(/Create Database Schema/i)).not.toBeInTheDocument();
    });

    test('search is case insensitive', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const searchInput = screen.getByPlaceholderText(/search tasks/i);
      fireEvent.change(searchInput, { target: { value: 'DATABASE' } });
      
      expect(screen.getByText(/Create Database Schema/i)).toBeInTheDocument();
    });

    test('combines search with filter', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      // Filter by pending
      const pendingBtn = screen.getByRole('button', { name: /pending/i });
      fireEvent.click(pendingBtn);
      
      // Search for "test"
      const searchInput = screen.getByPlaceholderText(/search tasks/i);
      fireEvent.change(searchInput, { target: { value: 'test' } });
      
      expect(screen.getByText(/Write Unit Tests/i)).toBeInTheDocument();
      expect(screen.queryByText(/Build Login Component/i)).not.toBeInTheDocument();
    });

    test('clears search when input is empty', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const searchInput = screen.getByPlaceholderText(/search tasks/i);
      fireEvent.change(searchInput, { target: { value: 'login' } });
      
      expect(screen.queryByText(/Initialize Project/i)).not.toBeInTheDocument();
      
      fireEvent.change(searchInput, { target: { value: '' } });
      
      expect(screen.getByText(/Initialize Project/i)).toBeInTheDocument();
    });
  });

  describe('Task Selection', () => {
    test('selects task on click', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const taskElement = screen.getByText(/Initialize Project/i).closest('.task-item');
      fireEvent.click(taskElement);
      
      expect(screen.getByText('Task Details')).toBeInTheDocument();
      expect(screen.getByText(/task-001/i)).toBeInTheDocument();
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });

    test('displays task output in detail panel', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const taskElement = screen.getByText(/Initialize Project/i).closest('.task-item');
      fireEvent.click(taskElement);
      
      expect(screen.getByText(/Project initialized successfully/i)).toBeInTheDocument();
    });

    test('displays task error in detail panel', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const failedTask = screen.getByText(/Setup CI\/CD Pipeline/i).closest('.task-item');
      fireEvent.click(failedTask);
      
      expect(screen.getByText(/Configuration file not found/i)).toBeInTheDocument();
    });

    test('displays agent information', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const taskElement = screen.getByText(/Initialize Project/i).closest('.task-item');
      fireEvent.click(taskElement);
      
      expect(screen.getByText(/opencode/i)).toBeInTheDocument();
    });

    test('calls onTaskSelect callback when task is selected', () => {
      const handleTaskSelect = jest.fn();
      render(<TaskDashboard tasks={mockTasks} onTaskSelect={handleTaskSelect} />);
      
      const taskElement = screen.getByText(/Initialize Project/i).closest('.task-item');
      fireEvent.click(taskElement);
      
      expect(handleTaskSelect).toHaveBeenCalledTimes(1);
      expect(handleTaskSelect).toHaveBeenCalledWith(mockTasks[0]);
    });
  });

  describe('CSS Classes', () => {
    test('applies correct status class for completed', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const completedTask = screen.getByText(/Initialize Project/i).closest('.task-item');
      expect(completedTask).toHaveClass('status-completed');
    });

    test('applies correct status class for in_progress', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const inProgressTask = screen.getByText(/Create Database Schema/i).closest('.task-item');
      expect(inProgressTask).toHaveClass('status-progress');
    });

    test('applies correct status class for pending', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const pendingTask = screen.getByText(/Build Login Component/i).closest('.task-item');
      expect(pendingTask).toHaveClass('status-pending');
    });

    test('applies correct status class for failed', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      const failedTask = screen.getByText(/Setup CI\/CD Pipeline/i).closest('.task-item');
      expect(failedTask).toHaveClass('status-failed');
    });
  });

  describe('Edge Cases', () => {
    test('handles tasks with missing optional fields', () => {
      const tasksWithMissingFields = [
        { id: 'task-001', status: 'pending' },
        { id: 'task-002', name: 'Task 2', status: 'completed' }
      ];
      
      render(<TaskDashboard tasks={tasksWithMissingFields} />);
      
      expect(screen.getByText('Task 2')).toBeInTheDocument();
      expect(screen.getByText(/task-001/i)).toBeInTheDocument();
    });

    test('handles unknown status gracefully', () => {
      const tasksWithUnknownStatus = [
        { id: 'task-001', name: 'Unknown Task', status: 'unknown_status' }
      ];
      
      render(<TaskDashboard tasks={tasksWithUnknownStatus} />);
      
      const taskElement = screen.getByText(/Unknown Task/i).closest('.task-item');
      expect(taskElement).toHaveClass('status-unknown');
    });

    test('handles special characters in search', () => {
      const tasksWithSpecialChars = [
        { id: 'task-001', name: 'Task: API Integration', status: 'pending' },
        { id: 'task-002', name: 'Task #2', status: 'completed' }
      ];
      
      render(<TaskDashboard tasks={tasksWithSpecialChars} />);
      
      const searchInput = screen.getByPlaceholderText(/search tasks/i);
      fireEvent.change(searchInput, { target: { value: 'API' } });
      
      expect(screen.getByText(/Task: API Integration/i)).toBeInTheDocument();
    });
  });

  describe('Props', () => {
    test('uses default empty array for tasks', () => {
      render(<TaskDashboard />);
      
      expect(screen.getByText('Task Dashboard')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
    });

    test('uses default refreshInterval', () => {
      render(<TaskDashboard tasks={mockTasks} />);
      
      // Component should render without errors with default props
      expect(screen.getByText('Task Dashboard')).toBeInTheDocument();
    });
  });
});
