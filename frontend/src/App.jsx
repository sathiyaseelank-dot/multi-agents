import { useState, useEffect } from 'react';
import './styles.css';

const API_BASE = 'http://localhost:5000/api/orchestrator';

function App() {
  const [task, setTask] = useState('');
  const [sessions, setSessions] = useState([]);
  const [runningSession, setRunningSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [activeTab, setActiveTab] = useState('run');

  // Fetch sessions on mount and every 5 seconds
  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${API_BASE}/sessions?limit=10`);
      const data = await response.json();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
  };

  const runTask = async () => {
    if (!task.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task }),
      });
      
      const data = await response.json();
      setRunningSession(data);
      setActiveTab('status');
      
      // Poll for status
      pollStatus(data.session_id);
    } catch (error) {
      console.error('Failed to run task:', error);
    } finally {
      setLoading(false);
    }
  };

  const pollStatus = async (sessionId) => {
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/status/${sessionId}`);
        const data = await response.json();
        
        if (data.status === 'running') {
          setRunningSession(data);
          setTimeout(poll, 3000);
        } else {
          setRunningSession(data);
          fetchSessions();
        }
      } catch (error) {
        console.error('Failed to poll status:', error);
      }
    };
    poll();
  };

  const viewResults = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE}/results/${sessionId}`);
      const data = await response.json();
      setSelectedSession(data);
      setActiveTab('results');
    } catch (error) {
      console.error('Failed to fetch results:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#22c55e';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🤖 Multi-Agent Orchestrator</h1>
        <p className="subtitle">AI Development Team OS</p>
      </header>

      <nav className="tabs">
        <button 
          className={activeTab === 'run' ? 'active' : ''}
          onClick={() => setActiveTab('run')}
        >
          New Task
        </button>
        <button 
          className={activeTab === 'status' ? 'active' : ''}
          onClick={() => setActiveTab('status')}
        >
          Status {runningSession && '(Running)'}
        </button>
        <button 
          className={activeTab === 'history' ? 'active' : ''}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
        <button 
          className={activeTab === 'results' ? 'active' : ''}
          onClick={() => setActiveTab('results')}
          disabled={!selectedSession}
        >
          Results
        </button>
      </nav>

      <main className="content">
        {activeTab === 'run' && (
          <div className="run-task">
            <h2>Run New Task</h2>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe what you want to build... (e.g., 'Build a REST API with user authentication using Flask and SQLite')"
              rows={5}
            />
            <button 
              className="primary"
              onClick={runTask}
              disabled={loading || !task.trim()}
            >
              {loading ? 'Starting...' : '🚀 Run Task'}
            </button>
            
            <div className="examples">
              <h3>Example Tasks:</h3>
              <ul>
                <li onClick={() => setTask('Build a Flask REST API with CRUD endpoints for a todo app')}
                    className="example-item">
                  📝 Build a Flask REST API with CRUD endpoints for a todo app
                </li>
                <li onClick={() => setTask('Build a chat application with authentication and real-time messaging')}
                    className="example-item">
                  💬 Build a chat application with authentication
                </li>
                <li onClick={() => setTask('Build a dashboard showing user analytics with charts')}
                    className="example-item">
                  📊 Build a dashboard showing user analytics
                </li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'status' && (
          <div className="status">
            <h2>Execution Status</h2>
            {runningSession ? (
              <div className="status-card">
                <div className="status-header">
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: getStatusColor(runningSession.status) }}
                  >
                    {runningSession.status}
                  </span>
                  <span className="session-id">{runningSession.session_id}</span>
                </div>
                <p className="task">{runningSession.task}</p>
                {runningSession.status === 'running' && (
                  <div className="loading">
                    <div className="spinner"></div>
                    <p>Executing task... This may take 2-5 minutes</p>
                  </div>
                )}
                {runningSession.events && runningSession.events.length > 0 && (
                  <div className="events">
                    <h3>Recent Events:</h3>
                    <div className="events-list">
                      {runningSession.events.slice(-10).map((event, idx) => (
                        <div key={idx} className="event-item">
                          <span className="event-type">{event.type}</span>
                          <span className="event-data">
                            {JSON.stringify(event.data).slice(0, 100)}...
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="no-data">No running session. Start a new task!</p>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="history">
            <h2>Session History</h2>
            {sessions.length > 0 ? (
              <table className="sessions-table">
                <thead>
                  <tr>
                    <th>Session ID</th>
                    <th>Task</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr key={session.session_id}>
                      <td className="session-id-cell">{session.session_id}</td>
                      <td className="task-cell">{session.task}</td>
                      <td>
                        <span 
                          className="status-badge"
                          style={{ backgroundColor: getStatusColor(session.status) }}
                        >
                          {session.status}
                        </span>
                      </td>
                      <td>{new Date(session.started_at).toLocaleString()}</td>
                      <td>
                        {session.status === 'completed' && (
                          <button 
                            className="small"
                            onClick={() => viewResults(session.session_id)}
                          >
                            View Results
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">No sessions yet. Run your first task!</p>
            )}
          </div>
        )}

        {activeTab === 'results' && selectedSession && (
          <div className="results">
            <h2>Results: {selectedSession.session_id}</h2>
            <div className="result-card">
              <div className="result-section">
                <h3>Status</h3>
                <span 
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(selectedSession.status) }}
                >
                  {selectedSession.status}
                </span>
              </div>
              
              {selectedSession.result && (
                <>
                  <div className="result-section">
                    <h3>Project Directory</h3>
                    <code>{selectedSession.result.project_dir}</code>
                  </div>
                  
                  <div className="result-section">
                    <h3>Build Result</h3>
                    <pre>{JSON.stringify(selectedSession.result.build_result, null, 2)}</pre>
                  </div>
                  
                  <div className="result-section">
                    <h3>Validation</h3>
                    <pre>{JSON.stringify(selectedSession.result.validation_result, null, 2)}</pre>
                  </div>
                  
                  <div className="result-section">
                    <h3>Runtime</h3>
                    <pre>{JSON.stringify(selectedSession.result.runtime_result, null, 2)}</pre>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
