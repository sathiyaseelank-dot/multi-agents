import React, { useState, useEffect } from 'react';

export interface Task {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  agent?: string;
  progress?: number;
  startedAt?: string;
  completedAt?: string;
  error?: string;
}

interface TaskStatusProps {
  tasks: Task[];
  onRetry?: (taskId: string) => void;
  onSkip?: (taskId: string) => void;
}

const statusColors = {
  pending: 'bg-gray-100 text-gray-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  skipped: 'bg-yellow-100 text-yellow-800',
};

const agentColors = {
  codex: 'bg-purple-500',
  opencode: 'bg-indigo-500',
  gemini: 'bg-cyan-500',
  kilo: 'bg-orange-500',
  default: 'bg-gray-500',
};

export const TaskStatus: React.FC<TaskStatusProps> = ({ tasks, onRetry, onSkip }) => {
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  const getStatusIcon = (status: Task['status']) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'running':
        return '🔄';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      case 'skipped':
        return '⏭️';
      default:
        return '❓';
    }
  };

  const formatTime = (dateString?: string) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleTimeString();
  };

  const getAgentBadge = (agent?: string) => {
    if (!agent) return null;
    const colorClass = agentColors[agent as keyof typeof agentColors] || agentColors.default;
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-white ${colorClass}`}>
        {agent}
      </span>
    );
  };

  return (
    <div className="w-full bg-white rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Task Execution Status</h2>
        <p className="text-sm text-gray-500 mt-1">
          {tasks.filter(t => t.status === 'completed').length} / {tasks.length} tasks completed
        </p>
      </div>

      <div className="divide-y divide-gray-200">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 flex-1">
                <span className="text-lg">{getStatusIcon(task.status)}</span>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-900">{task.name}</h3>
                  <p className="text-xs text-gray-500">ID: {task.id}</p>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {getAgentBadge(task.agent)}
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[task.status]}`}>
                  {task.status}
                </span>

                {task.status === 'failed' && onRetry && (
                  <button
                    onClick={() => onRetry(task.id)}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    Retry
                  </button>
                )}

                {task.status === 'pending' && onSkip && (
                  <button
                    onClick={() => onSkip(task.id)}
                    className="text-sm text-yellow-600 hover:text-yellow-800 font-medium"
                  >
                    Skip
                  </button>
                )}

                <button
                  onClick={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  {expandedTask === task.id ? '▲' : '▼'}
                </button>
              </div>
            </div>

            {task.progress !== undefined && task.status === 'running' && (
              <div className="mt-3">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">{task.progress}% complete</p>
              </div>
            )}

            {expandedTask === task.id && (
              <div className="mt-4 p-3 bg-gray-50 rounded-md text-sm">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-500">Started</p>
                    <p className="font-medium">{formatTime(task.startedAt)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Completed</p>
                    <p className="font-medium">{formatTime(task.completedAt)}</p>
                  </div>
                </div>
                {task.error && (
                  <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded">
                    <p className="text-xs text-red-800 font-medium">Error:</p>
                    <p className="text-xs text-red-600 mt-1">{task.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {tasks.length === 0 && (
        <div className="px-6 py-8 text-center text-gray-500">
          <p>No tasks to display</p>
        </div>
      )}
    </div>
  );
};

export default TaskStatus;
