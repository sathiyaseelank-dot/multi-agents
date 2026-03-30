import React from 'react';
import { Task } from '../types/task';
import { StatusBadge } from './StatusBadge';
import './TaskCard.css';

interface TaskCardProps {
  task: Task;
  onUpdate?: (taskId: string, updates: Partial<Task>) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({ task, onUpdate }) => {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const handleRetry = () => {
    onUpdate?.(task.id, { status: 'pending', error: undefined });
  };

  return (
    <div className={`task-card status-${task.status}`}>
      <div className="task-header">
        <h3 className="task-title">{task.description}</h3>
        <StatusBadge status={task.status} />
      </div>
      
      <div className="task-meta">
        <span className="task-id">#{task.id.split('-').pop()}</span>
        <span className="task-date">
          Created: {formatDate(task.createdAt)}
        </span>
      </div>

      {task.agent && (
        <div className="task-agent">
          <span>Agent: </span>
          <code>{task.agent}</code>
        </div>
      )}

      {task.progress !== undefined && (
        <div className="task-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <span>{task.progress}%</span>
        </div>
      )}

      {task.error && (
        <div className="task-error">
          <span className="error-icon">⚠</span>
          <span className="error-message">{task.error}</span>
          {task.status === 'failed' && (
            <button className="btn-retry" onClick={handleRetry}>
              Retry
            </button>
          )}
        </div>
      )}

      {task.result && (
        <div className="task-result">
          <a href={task.result} target="_blank" rel="noopener noreferrer">
            View Output
          </a>
        </div>
      )}
    </div>
  );
};
