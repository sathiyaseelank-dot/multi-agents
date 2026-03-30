import React, { useState, useEffect } from 'react';
import './TaskDashboard.css';

const TaskDashboard = ({ tasks = [], onTaskSelect, refreshInterval = 5000 }) => {
  const [filteredTasks, setFilteredTasks] = useState(tasks);
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTask, setSelectedTask] = useState(null);

  useEffect(() => {
    const filtered = tasks.filter(task => {
      const matchesStatus = filterStatus === 'all' || task.status === filterStatus;
      const matchesSearch = task.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           task.id?.toLowerCase().includes(searchTerm.toLowerCase());
      return matchesStatus && matchesSearch;
    });
    setFilteredTasks(filtered);
  }, [tasks, filterStatus, searchTerm]);

  const getStatusClass = (status) => {
    const statusMap = {
      'pending': 'status-pending',
      'in_progress': 'status-progress',
      'completed': 'status-completed',
      'failed': 'status-failed',
      'skipped': 'status-skipped'
    };
    return statusMap[status] || 'status-unknown';
  };

  const handleTaskClick = (task) => {
    setSelectedTask(task);
    if (onTaskSelect) {
      onTaskSelect(task);
    }
  };

  const stats = {
    total: tasks.length,
    completed: tasks.filter(t => t.status === 'completed').length,
    inProgress: tasks.filter(t => t.status === 'in_progress').length,
    failed: tasks.filter(t => t.status === 'failed').length,
    pending: tasks.filter(t => t.status === 'pending').length
  };

  const progress = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

  return (
    <div className="task-dashboard">
      <div className="dashboard-header">
        <h2 className="dashboard-title">Task Dashboard</h2>
        <div className="dashboard-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat-item completed">
            <span className="stat-value">{stats.completed}</span>
            <span className="stat-label">Completed</span>
          </div>
          <div className="stat-item in-progress">
            <span className="stat-value">{stats.inProgress}</span>
            <span className="stat-label">In Progress</span>
          </div>
          <div className="stat-item failed">
            <span className="stat-value">{stats.failed}</span>
            <span className="stat-label">Failed</span>
          </div>
        </div>
      </div>

      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${progress}%` }}></div>
        <span className="progress-text">{progress}% Complete</span>
      </div>

      <div className="dashboard-controls">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search tasks..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        <div className="filter-buttons">
          {['all', 'pending', 'in_progress', 'completed', 'failed'].map(status => (
            <button
              key={status}
              className={`filter-btn ${filterStatus === status ? 'active' : ''}`}
              onClick={() => setFilterStatus(status)}
            >
              {status.replace('_', ' ').toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="task-list">
        {filteredTasks.length === 0 ? (
          <div className="no-tasks">
            <p>No tasks found</p>
          </div>
        ) : (
          filteredTasks.map(task => (
            <div
              key={task.id}
              className={`task-item ${selectedTask?.id === task.id ? 'selected' : ''}`}
              onClick={() => handleTaskClick(task)}
            >
              <div className="task-info">
                <h4 className="task-name">{task.name || task.id}</h4>
                {task.description && (
                  <p className="task-description">{task.description}</p>
                )}
                <div className="task-meta">
                  <span className="task-agent">Agent: {task.agent || 'N/A'}</span>
                  {task.duration && (
                    <span className="task-duration">Duration: {task.duration}s</span>
                  )}
                </div>
              </div>
              <div className={`task-status ${getStatusClass(task.status)}`}>
                {task.status}
              </div>
            </div>
          ))
        )}
      </div>

      {selectedTask && (
        <div className="task-detail-panel">
          <h3>Task Details</h3>
          <div className="detail-row">
            <strong>ID:</strong> {selectedTask.id}
          </div>
          <div className="detail-row">
            <strong>Status:</strong> {selectedTask.status}
          </div>
          <div className="detail-row">
            <strong>Agent:</strong> {selectedTask.agent || 'N/A'}
          </div>
          {selectedTask.output && (
            <div className="detail-row">
              <strong>Output:</strong>
              <pre className="task-output">{selectedTask.output}</pre>
            </div>
          )}
          {selectedTask.error && (
            <div className="detail-row error">
              <strong>Error:</strong>
              <pre className="task-error">{selectedTask.error}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TaskDashboard;
