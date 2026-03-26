import { useState, useEffect } from 'react';
import './styles.css';

const API_BASE = 'http://localhost:5000/api/orchestrator';

const PLAN_EVENT_TYPES = ['plan_created', 'plan_revised'];

function getLivePlan(session) {
  if (!session) return null;

  if (session.plan) return session.plan;
  if (session.result?.plan) return session.result.plan;
  if (session.result?.planning_trace?.revised_plan) return session.result.planning_trace.revised_plan;
  if (session.result?.planning_trace?.initial_plan) return session.result.planning_trace.initial_plan;
  if (session.planning_trace?.revised_plan) return session.planning_trace.revised_plan;
  if (session.planning_trace?.initial_plan) return session.planning_trace.initial_plan;

  const latestPlanEvent = [...(session.events || [])]
    .reverse()
    .find((event) => PLAN_EVENT_TYPES.includes(event.type) && event.data?.plan);

  return latestPlanEvent?.data?.plan || null;
}

function getPlanningTrace(session) {
  return session?.result?.planning_trace || session?.planning_trace || null;
}

function getLiveSummary(session) {
  return session?.result?.summary || session?.summary || null;
}

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
        const statusRes = await fetch(`${API_BASE}/status/${sessionId}`);
        const statusData = await statusRes.json();
        
        if (statusData.status === 'running') {
          const resultsRes = await fetch(`${API_BASE}/results/${sessionId}`);
          if (resultsRes.ok) {
            const resultsData = await resultsRes.json();
            setRunningSession({ ...statusData, ...resultsData });
          } else {
            setRunningSession(statusData);
          }
          setTimeout(poll, 2000);
        } else {
          setRunningSession(statusData);
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

  const currentPlan = getLivePlan(runningSession);
  const planningTrace = getPlanningTrace(runningSession);
  const planSummary = getLiveSummary(runningSession);
  const orchestrationPhases =
    currentPlan?.phases ||
    planningTrace?.revised_plan?.phases ||
    planningTrace?.initial_plan?.phases ||
    [];

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
                <p className="task">{runningSession.task || runningSession.result?.goal_analysis?.original_goal}</p>
                
                {runningSession.status === 'running' && (
                  <div className="loading">
                    <div className="spinner"></div>
                    <p>{currentPlan ? 'Executing orchestration plan below.' : 'Generating execution plan...'}</p>
                  </div>
                )}

                {currentPlan?.tasks && (
                  <div className="plan-section">
                    <h3>Execution Plan</h3>
                    <div className="tasks-list">
                      {currentPlan.tasks.map((task) => (
                        <div key={task.id} className="task-item">
                          <span className="task-id">{task.id}</span>
                          <span className="task-title">{task.title}</span>
                          <span className="task-agent">{task.agent}</span>
                          <span className="task-meta">{task.type}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {planSummary?.tasks && (
                  <div className="plan-progress">
                    <h3>Plan Progress</h3>
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ 
                          width: `${((planSummary.counts?.completed || 0) / (planSummary.total || 1)) * 100}%` 
                        }}
                      />
                    </div>
                    <p className="progress-text">
                      {planSummary.counts?.completed || 0} / {planSummary.total} tasks completed
                    </p>
                    <div className="tasks-list">
                      {planSummary.tasks.map((task) => (
                        <div key={task.id} className={`task-item ${task.status}`}>
                          <span className="task-id">{task.id}</span>
                          <span className="task-title">{task.title}</span>
                          <span className="task-agent">{task.agent}</span>
                          <span className={`task-status ${task.status}`}>
                            {task.status === 'completed' ? '✓' : task.status === 'running' ? '⟳' : task.status === 'failed' ? '✗' : '○'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {orchestrationPhases.length > 0 && (
                  <div className="phases">
                    <h3>Orchestration Plan</h3>
                    {orchestrationPhases.map((phase) => (
                      <div key={phase.phase} className="phase-item">
                        <span className="phase-num">Phase {phase.phase}</span>
                        <span className="phase-desc">{phase.description}</span>
                        <span className="phase-tasks">{phase.task_ids.join(', ')}</span>
                      </div>
                    ))}
                  </div>
                )}

                {planningTrace && (
                  <div className="plan-section">
                    <h3>Planning Review</h3>
                    <div className="review-grid">
                      {planningTrace.review_1 && (
                        <div className="review-item">
                          <strong>Review 1</strong>
                          <span>{planningTrace.review_1.approval ? 'Approved' : 'Rejected'}</span>
                          <span>Confidence: {planningTrace.review_1.confidence ?? 'n/a'}</span>
                        </div>
                      )}
                      {planningTrace.review_2 && (
                        <div className="review-item">
                          <strong>Review 2</strong>
                          <span>{planningTrace.review_2.approval ? 'Approved' : 'Rejected'}</span>
                          <span>Confidence: {planningTrace.review_2.confidence ?? 'n/a'}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                {runningSession.events && runningSession.events.length > 0 && (
                  <div className="events">
                    <h3>Recent Events</h3>
                    <div className="events-list">
                      {runningSession.events.slice(-15).map((event, idx) => (
                        <div key={idx} className="event-item">
                          <span className="event-type">{event.type}</span>
                          <span className="event-data">
                            {event.type === 'phase_started' && `Phase ${event.data?.phase}`}
                            {event.type === 'phase_completed' && `Phase ${event.data?.phase} done`}
                            {event.type === 'task_started' && `${event.data?.task_id}: ${event.data?.title}`}
                            {event.type === 'task_completed' && `${event.data?.task_id}: SUCCESS`}
                            {event.type === 'task_failed' && `${event.data?.task_id}: FAILED`}
                            {event.type === 'info' && event.data?.message?.slice(0, 60)}
                            {!['phase_started', 'phase_completed', 'task_started', 'task_completed', 'task_failed', 'info'].includes(event.type) && 
                              JSON.stringify(event.data)?.slice(0, 80)}
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
