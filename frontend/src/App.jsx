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
    
    // Check for running session in localStorage
    const savedSessionId = localStorage.getItem('runningSessionId');
    if (savedSessionId) {
      restoreRunningSession(savedSessionId);
    }
    
    return () => clearInterval(interval);
  }, []);
  
  const restoreRunningSession = async (sessionId) => {
    try {
      const statusRes = await fetch(`${API_BASE}/status/${sessionId}`);
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        if (statusData.status === 'running') {
          setRunningSession(statusData);
          setActiveTab('status');
          pollStatus(sessionId);
        } else {
          localStorage.removeItem('runningSessionId');
        }
      }
    } catch (error) {
      console.error('Failed to restore running session:', error);
    }
  };

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
      
      // Save session ID to localStorage
      localStorage.setItem('runningSessionId', data.session_id);
      
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
          
          // Also try to fetch checkpoint for live file updates
          try {
            const checkpointRes = await fetch(`${API_BASE}/checkpoint/${sessionId}`);
            if (checkpointRes.ok) {
              const checkpointData = await checkpointRes.json();
              setRunningSession(prev => ({ ...prev, checkpoint: checkpointData }));
            }
          } catch (e) {
            // Checkpoint endpoint might not exist, ignore
          }
          
          setTimeout(poll, 2000);
        } else {
          setRunningSession(statusData);
          fetchSessions();
          localStorage.removeItem('runningSessionId');
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
                  <div className="live-activity">
                    <h3>Live Agent Activity</h3>
                    
                    {(() => {
                      const events = runningSession.events || [];
                      const lastTaskStarted = [...events].reverse().find(e => e.type === 'task_started');
                      const lastTaskCompleted = [...events].reverse().find(e => e.type === 'task_completed');
                      const lastPhaseStarted = [...events].reverse().find(e => e.type === 'phase_started');
                      const currentPhase = lastPhaseStarted?.data;
                      
                      return (
                        <>
                          <div className="current-status">
                            {lastTaskStarted && !lastTaskCompleted && (
                              <div className="status-running">
                                <div className="spinner-small"></div>
                                <span><strong>{lastTaskStarted.data?.agent?.toUpperCase()}</strong> is working on: <em>{lastTaskStarted.data?.title}</em></span>
                              </div>
                            )}
                            {lastTaskCompleted && !lastTaskStarted && (
                              <div className="status-waiting">
                                <span>⏳ Waiting for next task...</span>
                              </div>
                            )}
                            {currentPhase && (
                              <div className="phase-info">
                                Phase {currentPhase.phase}/{currentPhase.total_phases} — {currentPhase.mode?.toUpperCase()} mode
                              </div>
                            )}
                          </div>
                          
                          <div className="activity-feed">
                            {events.slice(-12).map((event, idx) => {
                              const isNew = idx === events.length - 1;
                              return (
                                <div key={idx} className={`activity-item ${event.type} ${isNew ? 'new' : ''}`}>
                                  <span className="activity-icon">
                                    {event.type === 'task_started' && '⚡'}
                                    {event.type === 'task_completed' && '✅'}
                                    {event.type === 'task_failed' && '❌'}
                                    {event.type === 'phase_started' && '🚀'}
                                    {event.type === 'phase_completed' && '📦'}
                                    {event.type === 'info' && '💬'}
                                    {event.type === 'warning' && '⚠️'}
                                    {event.type === 'plan_created' && '📝'}
                                    {event.type === 'plan_review_completed' && '🔍'}
                                    {event.type === 'plan_approved' && '👍'}
                                    {event.type === 'run_started' && '▶️'}
                                    {!['task_started', 'task_completed', 'task_failed', 'phase_started', 'phase_completed', 'info', 'warning', 'plan_created', 'plan_review_completed', 'plan_approved', 'run_started'].includes(event.type) && '📋'}
                                  </span>
                                  <span className="activity-content">
                                    {event.type === 'task_started' && (
                                      <span>
                                        <strong>{event.data?.agent?.toUpperCase()}</strong> → {event.data?.title}
                                      </span>
                                    )}
                                    {event.type === 'task_completed' && (
                                      <span>
                                        <strong>{event.data?.agent?.toUpperCase()}</strong> ✅ {event.data?.execution_time?.toFixed(1)}s
                                        {event.data?.summary && <span className="task-summary-text"> — {event.data.summary.slice(0, 60)}{event.data.summary?.length > 60 ? '...' : ''}</span>}
                                      </span>
                                    )}
                                    {event.type === 'task_failed' && (
                                      <span>
                                        <strong>{event.data?.agent?.toUpperCase()}</strong> ❌ {event.data?.error?.slice(0, 50)}
                                      </span>
                                    )}
                                    {event.type === 'phase_started' && (
                                      <span>🚀 Phase {event.data?.phase}/{event.data?.total_phases}: {event.data?.task_ids?.join(', ')}</span>
                                    )}
                                    {event.type === 'phase_completed' && (
                                      <span>📦 Phase {event.data?.phase} done</span>
                                    )}
                                    {event.type === 'info' && (
                                      <span>{event.data?.message}</span>
                                    )}
                                    {event.type === 'warning' && (
                                      <span className="warning-text">⚠️ {event.data?.message}</span>
                                    )}
                                    {event.type === 'plan_created' && (
                                      <span>📝 Plan: {event.data?.task_count} tasks, {event.data?.phase_count} phases</span>
                                    )}
                                    {event.type === 'plan_review_completed' && (
                                      <span>🔍 Review {event.data?.iteration}: {event.data?.approval ? 'Approved' : 'Rejected'} ({event.data?.confidence})</span>
                                    )}
                                    {event.type === 'plan_approved' && (
                                      <span>👍 Plan approved</span>
                                    )}
                                    {!['task_started', 'task_completed', 'task_failed', 'phase_started', 'phase_completed', 'info', 'warning', 'plan_created', 'plan_review_completed', 'plan_approved', 'run_started'].includes(event.type) && (
                                      <span>{JSON.stringify(event.data)?.slice(0, 80)}</span>
                                    )}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </>
                      );
                    })()}
                    
                    {runningSession.checkpoint?.tasks && Object.keys(runningSession.checkpoint.tasks).length > 0 && (
                      <div className="generated-files">
                        <h4>Files Generated</h4>
                        <div className="project-location">
                          📁 Project: <code>project/{runningSession.session_id}/</code>
                        </div>
                        <div className="files-list">
                          {Object.values(runningSession.checkpoint.tasks)
                            .filter(t => t.status === 'success' && t.result?.files_created?.length > 0)
                            .map(task => (
                              <div key={task.id} className="task-files">
                                <strong>{task.id}:</strong>
                                <div className="file-items">
                                  {task.result.files_created.map((file, i) => (
                                    <span key={i} className="file-badge">{file}</span>
                                  ))}
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
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
                  {selectedSession.result.summary && (
                    <div className="result-section">
                      <h3>Task Summary</h3>
                      <div className="task-summary">
                        <p>Total: {selectedSession.result.summary.total} | Completed: {selectedSession.result.summary.counts?.success || 0} | Failed: {selectedSession.result.summary.counts?.failed || 0}</p>
                        <div className="tasks-list">
                          {selectedSession.result.summary.tasks?.map((task) => (
                            <div key={task.id} className={`task-item ${task.status}`}>
                              <span className="task-id">{task.id}</span>
                              <span className="task-title">{task.title}</span>
                              <span className="task-agent">{task.agent}</span>
                              <span className={`task-status ${task.status}`}>
                                {task.status === 'success' ? '✓' : task.status === 'failed' ? '✗' : task.status === 'running' ? '⟳' : '○'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {selectedSession.result.summary?.counts?.success > 0 && (
                    <div className="result-section">
                      <h3>Generated Files</h3>
                      <div className="project-location">
                        📁 Project Location: <code>flask_api/project/{selectedSession.session_id}/</code>
                      </div>
                    </div>
                  )}
                  
                  {selectedSession.result.goal_analysis && (
                    <div className="result-section">
                      <h3>Goal Analysis</h3>
                      <pre>{JSON.stringify(selectedSession.result.goal_analysis, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.result.project_build && Object.keys(selectedSession.result.project_build).length > 0 && (
                    <div className="result-section">
                      <h3>Project Build</h3>
                      <pre>{JSON.stringify(selectedSession.result.project_build, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.result.validation && Object.keys(selectedSession.result.validation).length > 0 && (
                    <div className="result-section">
                      <h3>Validation</h3>
                      <pre>{JSON.stringify(selectedSession.result.validation, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.result.runtime && Object.keys(selectedSession.result.runtime).length > 0 && (
                    <div className="result-section">
                      <h3>Runtime</h3>
                      <pre>{JSON.stringify(selectedSession.result.runtime, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.result.evaluation && Object.keys(selectedSession.result.evaluation).length > 0 && (
                    <div className="result-section">
                      <h3>Evaluation</h3>
                      <pre>{JSON.stringify(selectedSession.result.evaluation, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.result.final_review && (
                    <div className="result-section">
                      <h3>Final Review</h3>
                      <pre>{JSON.stringify(selectedSession.result.final_review, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.result.planning_trace && (
                    <div className="result-section">
                      <h3>Planning Trace</h3>
                      <pre>{JSON.stringify(selectedSession.result.planning_trace, null, 2)}</pre>
                    </div>
                  )}
                  
                  {selectedSession.events && selectedSession.events.length > 0 && (
                    <div className="result-section">
                      <h3>Events ({selectedSession.events.length})</h3>
                      <div className="events-list">
                        {selectedSession.events.slice(-20).map((event, idx) => (
                          <div key={idx} className="event-item">
                            <span className="event-type">{event.type}</span>
                            <span className="event-data">
                              {JSON.stringify(event.data)?.slice(0, 100)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
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
