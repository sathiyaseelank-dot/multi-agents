import React from 'react';
import ReactDOM from 'react-dom/client';
import TaskDashboard from './TaskDashboard';

// Example usage with mock data
const mockTasks = [
  {
    id: 'task-001',
    name: 'Initialize Project',
    description: 'Set up project structure and dependencies',
    status: 'completed',
    agent: 'opencode',
    duration: 12.5,
    output: 'Project initialized successfully'
  },
  {
    id: 'task-002',
    name: 'Create Database Schema',
    description: 'Design and implement database models',
    status: 'in_progress',
    agent: 'opencode',
    duration: 8.3
  },
  {
    id: 'task-003',
    name: 'Build Login Component',
    description: 'Create React login form with validation',
    status: 'pending',
    agent: 'gemini'
  },
  {
    id: 'task-004',
    name: 'Write Unit Tests',
    description: 'Add test coverage for auth module',
    status: 'pending',
    agent: 'kilo'
  },
  {
    id: 'task-005',
    name: 'Setup CI/CD Pipeline',
    description: 'Configure automated testing and deployment',
    status: 'failed',
    agent: 'opencode',
    error: 'Configuration file not found: .github/workflows/ci.yml'
  }
];

const App = () => {
  const handleTaskSelect = (task) => {
    console.log('Selected task:', task);
  };

  return (
    <div style={{ padding: '20px', background: '#fafafa', minHeight: '100vh' }}>
      <TaskDashboard
        tasks={mockTasks}
        onTaskSelect={handleTaskSelect}
        refreshInterval={5000}
      />
    </div>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

export default App;
