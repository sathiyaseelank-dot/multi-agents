import React, { useState, useEffect } from 'react';
import './TaskDashboard.css';

const TaskDashboard = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await fetch('/api/orchestrator/sessions');
        if (!response.ok) throw new Error('Failed to fetch tasks');
        const data = await response.json();
        setTasks(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, []);

  const getStatusColor = (status) => {
    const colors = {
      COMPLETED: '#22c55e',
      FAILED: '#ef4444',
      EXECUTING: '#3b82f6',
      PLANNING: '#f59e0b',
      VALIDATING: '#8b5cf6',
      RUNNING: '#06b6d4',
    };
    return colors[status] || '#6b7280';
  };

  if (loading) return <div className="loading">Loading tasks...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="task-dashboard">
      <h1>Task Dashboard</h1>
      <div className="task-list">
        {tasks.length === 0 ? (
          <p className="no-tasks">No tasks found</p>
        ) : (
          tasks.map((task, index) => (
            <div key={index} className="task-card">
              <div className="task-header">
                <span className="task-id">{task.session_id}</span>
                <span
                  className="task-status"
                  style={{ backgroundColor: getStatusColor(task.status) }}
                >
                  {task.status}
                </span>
              </div>
              <p className="task-description">{task.task_description}</p>
              <div className="task-meta">
                <span>Created: {task.created_at}</span>
                <span>Tasks: {task.task_count || 0}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TaskDashboard;
