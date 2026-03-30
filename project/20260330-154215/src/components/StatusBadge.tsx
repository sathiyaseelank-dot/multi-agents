import React from 'react';
import { TaskStatus } from '../types/task';
import './StatusBadge.css';

interface StatusBadgeProps {
  status: TaskStatus;
}

const statusConfig: Record<TaskStatus, { label: string; icon: string }> = {
  pending: { label: 'Pending', icon: '⏳' },
  planning: { label: 'Planning', icon: '📋' },
  running: { label: 'Running', icon: '▶️' },
  completed: { label: 'Completed', icon: '✅' },
  failed: { label: 'Failed', icon: '❌' }
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config = statusConfig[status] || statusConfig.pending;
  
  return (
    <span className={`status-badge status-${status}`}>
      <span className="status-icon">{config.icon}</span>
      <span className="status-label">{config.label}</span>
    </span>
  );
};
