import React, { useState, useEffect } from 'react';
import { Task, TaskStatus } from '../types/task';
import { StatusBadge } from './StatusBadge';
import { TaskCard } from './TaskCard';
import { TaskForm } from './TaskForm';
import './TaskDashboard.css';

interface TaskDashboardProps {
  onTaskSubmit?: (task: string) => void;
  initialTasks?: Task[];
}

export const TaskDashboard: React.FC<TaskDashboardProps> = ({
  onTaskSubmit,
  initialTasks = []
}) => {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [filter, setFilter] = useState<TaskStatus | 'all'>('all');
  const [showForm, setShowForm] = useState(false);

  const filteredTasks = tasks.filter(task => 
    filter === 'all' ? true : task.status === filter
  );

  const handleTaskSubmit = (taskDescription: string) => {
    const newTask: Task = {
      id: `task-${Date.now()}`,
      description: taskDescription,
      status: 'pending',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    setTasks(prev => [newTask, ...prev]);
    setShowForm(false);
    onTaskSubmit?.(taskDescription);
  };

  const handleTaskUpdate = (taskId: string, updates: Partial<Task>) => {
    setTasks(prev => prev.map(task => 
      task.id === taskId 
        ? { ...task, ...updates, updatedAt: new Date().toISOString() }
        : task
    ));
  };

  const stats = {
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    running: tasks.filter(t => t.status === 'running').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length
  };

  return (
    <div className="task-dashboard">
      <header className="dashboard-header">
        <h1>Multi-Agent Orchestrator</h1>
        <button 
          className="btn-primary"
          onClick={() => setShowForm(true)}
        >
          + New Task
        </button>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-value">{stats.total}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat-card pending">
          <span className="stat-value">{stats.pending}</span>
          <span className="stat-label">Pending</span>
        </div>
        <div className="stat-card running">
          <span className="stat-value">{stats.running}</span>
          <span className="stat-label">Running</span>
        </div>
        <div className="stat-card completed">
          <span className="stat-value">{stats.completed}</span>
          <span className="stat-label">Completed</span>
        </div>
        <div className="stat-card failed">
          <span className="stat-value">{stats.failed}</span>
          <span className="stat-label">Failed</span>
        </div>
      </div>

      <div className="filter-bar">
        <span>Filter:</span>
        <button 
          className={filter === 'all' ? 'active' : ''}
          onClick={() => setFilter('all')}
        >
          All
        </button>
        <button 
          className={filter === 'pending' ? 'active' : ''}
          onClick={() => setFilter('pending')}
        >
          Pending
        </button>
        <button 
          className={filter === 'running' ? 'active' : ''}
          onClick={() => setFilter('running')}
        >
          Running
        </button>
        <button 
          className={filter === 'completed' ? 'active' : ''}
          onClick={() => setFilter('completed')}
        >
          Completed
        </button>
        <button 
          className={filter === 'failed' ? 'active' : ''}
          onClick={() => setFilter('failed')}
        >
          Failed
        </button>
      </div>

      <div className="tasks-grid">
        {filteredTasks.map(task => (
          <TaskCard 
            key={task.id} 
            task={task}
            onUpdate={handleTaskUpdate}
          />
        ))}
        {filteredTasks.length === 0 && (
          <div className="empty-state">
            <p>No tasks found</p>
            <button 
              className="btn-secondary"
              onClick={() => setShowForm(true)}
            >
              Create your first task
            </button>
          </div>
        )}
      </div>

      {showForm && (
        <TaskForm
          onSubmit={handleTaskSubmit}
          onCancel={() => setShowForm(false)}
        />
      )}
    </div>
  );
};
