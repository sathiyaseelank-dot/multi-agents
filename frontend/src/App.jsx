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

function getLivePhases(session) {
  if (!session) return [];
  return (
    session.phases ||
    session.result?.phases ||
    session.plan?.phases ||
    session.result?.plan?.phases ||
    session.result?.planning_trace?.revised_plan?.phases ||
    session.result?.planning_trace?.initial_plan?.phases ||
    session.planning_trace?.revised_plan?.phases ||
    session.planning_trace?.initial_plan?.phases ||
    []
  );
}

function getDisabledAgents(session) {
  if (!session) return [];
  return session.disabled_agents || session.result?.disabled_agents || [];
}

function getExecutionSummary(session) {
  if (!session) return '';
  return session.execution_summary || session.result?.execution_summary || '';
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
          if (resultsRes.ok && resultsRes.status === 200) {
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
  const orchestrationPhases = getLivePhases(runningSession);
  const disabledAgents = getDisabledAgents(runningSession);
  const executionSummary = getExecutionSummary(runningSession);

  return (
    <div className="app">
      <header className="header">
        <h1>🤖 MULTI-AGENT ORCHESTRATOR</h1>
        <p className="subtitle">AI Development Team OS</p>
      </header>

      <nav className="nav">
        <button className={activeTab === 'run' ? 'active' : ''} onClick={() => setActiveTab('run')}>New Task</button>
        <button className={activeTab === 'status' ? 'active' : ''} onClick={() => setActiveTab('status')}>
          Status {runningSession && '(Running)'}
        </button>
        <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}>History</button>
        <button className={activeTab === 'results' ? 'active' : ''} onClick={() => setActiveTab('results')} disabled={!selectedSession}>Results</button>
      </nav>

      <main className="main">
        {activeTab === 'run' && (
          <div className="run-tab">
            <h2>RUN NEW TASK</h2>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe what you want to build... (e.g., 'Build a REST API with user authentication using Flask and SQLite')"
              rows={5}
            />
            <button onClick={runTask} disabled={loading}>
              {loading ? 'Starting...' : '🚀 Run Task'}
            </button>

            <div className="examples">
              <h3>EXAMPLE TASKS:</h3>
              <ul>
                <li onClick={() => setTask('Build a Flask REST API with CRUD endpoints for a todo app')} className="example-item">📝 Build a Flask REST API with CRUD endpoints for a todo app</li>
                <li onClick={() => setTask('Build a chat application with authentication and real-time messaging')} className="example-item">💬 Build a chat application with authentication</li>
                <li onClick={() => setTask('Build a dashboard showing user analytics with charts')} className="example-item">📊 Build a dashboard showing user analytics</li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === 'status' && (
          <div className="status-tab">
            <h2>EXECUTION STATUS</h2>
            {runningSession ? (
              <div>
                <div className="status-badge" style={{ backgroundColor: getStatusColor(runningSession.status) }}>
                  {runningSession.status}
                </div>
                <p className="session-id">Session: {runningSession.session_id}</p>
                <p className="task">{runningSession.task || runningSession.result?.goal_analysis?.original_goal}</p>

                {runningSession.status === 'running' && (
                  <div className="live-status">
                    <h3>LIVE AGENT ACTIVITY</h3>
                    {(() => {
                      const events = runningSession.events || [];
                      const lastTaskStarted = [...events].reverse().find(e => e.type === 'task_started');
                      const lastTaskCompleted = [...events].reverse().find(e => e.type === 'task_completed');
                      const lastPhaseStarted = [...events].reverse().find(e => e.type === 'phase_started');
                      const currentPhase = lastPhaseStarted?.data;
                      return (
                        <>
                          {lastTaskStarted && !lastTaskCompleted && (
                            <div className="current-task">
                              <strong>{lastTaskStarted.data?.agent?.toUpperCase()}</strong> is working on: {lastTaskStarted.data?.title}
                            </div>
                          )}
                          {lastTaskCompleted && !lastTaskStarted && (
                            <div className="waiting">⏳ Waiting for next task...</div>
                          )}
                          {currentPhase && (
                            <div className="phase-info">
                              Phase {currentPhase.phase}/{currentPhase.total_phases} - {currentPhase.mode?.toUpperCase()} mode
                            </div>
                          )}
                          <div className="events-feed">
                            {events.slice(-12).map((event, idx) => {
                              const isNew = idx === events.length - 1;
                              return (
                                <div key={idx} className={`event ${isNew ? 'new' : ''}`}>
                                  <span className="event-icon">
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
                                  <span className="event-text">
                                    {event.type === 'task_started' && (
                                      <><strong>{event.data?.agent?.toUpperCase()}</strong> {'->'} {event.data?.title}</>
                                    )}
                                    {event.type === 'task_completed' && (
                                      <><strong>{event.data?.agent?.toUpperCase()}</strong> ✅ {event.data?.execution_time?.toFixed(1)}s
                                      {event.data?.summary && ` - ${event.data.summary.slice(0, 60)}${event.data.summary?.length > 60 ? '...' : ''}`}</>
                                    )}
                                    {event.type === 'task_failed' && (
                                      <><strong>{event.data?.agent?.toUpperCase()}</strong> ❌ {event.data?.error?.slice(0, 50)}</>
                                    )}
                                    {event.type === 'phase_started' && (
                                      <>🚀 Phase {event.data?.phase}/{event.data?.total_phases}: {event.data?.task_ids?.join(', ')}</>
                                    )}
                                    {event.type === 'phase_completed' && (
                                      <>📦 Phase {event.data?.phase} done</>
                                    )}
                                    {event.type === 'info' && (
                                      <>{event.data?.message}</>
                                    )}
                                    {event.type === 'warning' && (
                                      <>⚠️ {event.data?.message}</>
                                    )}
                                    {event.type === 'plan_created' && (
                                      <>📝 Plan: {event.data?.task_count} tasks, {event.data?.phase_count} phases</>
                                    )}
                                    {event.type === 'plan_review_completed' && (
                                      <>🔍 Review {event.data?.iteration}: {event.data?.approval ? 'Approved' : 'Rejected'} ({event.data?.confidence})</>
                                    )}
                                    {event.type === 'plan_approved' && (
                                      <>👍 Plan approved</>
                                    )}
                                    {!['task_started', 'task_completed', 'task_failed', 'phase_started', 'phase_completed', 'info', 'warning', 'plan_created', 'plan_review_completed', 'plan_approved', 'run_started'].includes(event.type) && (
                                      <>{JSON.stringify(event.data)?.slice(0, 80)}</>
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
                      <div className="files-generated">
                        <h4>FILES GENERATED</h4>
                        <p>📁 Project: project/{runningSession.session_id}/</p>
                        {Object.values(runningSession.checkpoint.tasks)
                          .filter(t => t.status === 'success' && t.result?.files_created?.length > 0)
                          .map(task => (
                            <div key={task.id} className="task-files">
                              <strong>{task.id}:</strong>
                              <ul>
                                {task.result.files_created.map((file, i) => (
                                  <li key={i}>{file}</li>
                                ))}
                              </ul>
                            </div>
                          ))
                        }
                      </div>
                    )}

                    {currentPlan?.tasks && (
                      <div className="plan-section">
                        <h3>EXECUTION PLAN</h3>
                        <table>
                          <thead>
                            <tr>
                              <th>ID</th>
                              <th>Title</th>
                              <th>Agent</th>
                              <th>Type</th>
                            </tr>
                          </thead>
                          <tbody>
                            {currentPlan.tasks.map((task) => (
                              <tr key={task.id}>
                                <td>{task.id}</td>
                                <td>{task.title}</td>
                                <td>{task.agent}</td>
                                <td>{task.type}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {disabledAgents.length > 0 && (
                      <div className="agent-health-section">
                        <h3>DISABLED AGENTS</h3>
                        <div className="disabled-agent-list">
                          {disabledAgents.map((item) => (
                            <div key={item.agent} className="disabled-agent-item">
                              <strong>{item.agent}</strong>
                              <span>{item.reason}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {planSummary?.tasks && (
                      <div className="progress-section">
                        <h3>PLAN PROGRESS</h3>
                        <p>{planSummary.counts?.completed || 0} / {planSummary.total} tasks completed</p>
                        <div className="task-list">
                          {planSummary.tasks.map((task) => (
                            <div key={task.id} className={`task-item ${task.status}`}>
                              <span className="task-id">{task.id}</span>
                              <span className="task-title">{task.title}</span>
                              <span className="task-agent">{task.agent}</span>
                              <span className="task-status">
                                {task.status === 'completed' ? '✓' : task.status === 'running' ? '⟳' : task.status === 'failed' ? '✗' : '○'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {orchestrationPhases.length > 0 && (
                      <div className="orchestration-section">
                        <h3>ORCHESTRATION PLAN</h3>
                        {orchestrationPhases.map((phase) => (
                          <div key={phase.phase} className="phase-item">
                            <strong>Phase {phase.phase}</strong>
                            <span>{phase.description}</span>
                            <code>{phase.task_ids.join(', ')}</code>
                          </div>
                        ))}
                      </div>
                    )}

                    {executionSummary && (
                      <div className="execution-summary-section">
                        <h3>EXECUTION ORDER</h3>
                        <pre>{executionSummary}</pre>
                      </div>
                    )}

                    {planningTrace && (
                      <div className="planning-section">
                        <h3>PLANNING REVIEW</h3>
                        {planningTrace.review_1 && (
                          <div className="review">
                            <strong>Review 1</strong>
                            <span>{planningTrace.review_1.approval ? 'Approved' : 'Rejected'}</span>
                            <span>Confidence: {planningTrace.review_1.confidence ?? 'n/a'}</span>
                          </div>
                        )}
                        {planningTrace.review_2 && (
                          <div className="review">
                            <strong>Review 2</strong>
                            <span>{planningTrace.review_2.approval ? 'Approved' : 'Rejected'}</span>
                            <span>Confidence: {planningTrace.review_2.confidence ?? 'n/a'}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {runningSession.events && runningSession.events.length > 0 && (
                      <div className="events-section">
                        <h3>RECENT EVENTS</h3>
                        <div className="events-list">
                          {runningSession.events.slice(-15).map((event, idx) => (
                            <div key={idx} className="event-item">
                              <strong>{event.type}</strong>
                              <span>
                                {event.type === 'phase_started' && `Phase ${event.data?.phase}`}
                                {event.type === 'phase_completed' && `Phase ${event.data?.phase} done`}
                                {event.type === 'task_started' && `${event.data?.task_id}: ${event.data?.title}`}
                                {event.type === 'task_completed' && `${event.data?.task_id}: SUCCESS`}
                                {event.type === 'task_failed' && `${event.data?.task_id}: FAILED`}
                                {event.type === 'info' && event.data?.message?.slice(0, 60)}
                                {!['phase_started', 'phase_completed', 'task_started', 'task_completed', 'task_failed', 'info'].includes(event.type) && JSON.stringify(event.data)?.slice(0, 80)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="no-session">
                <p>No running session. Start a new task!</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="history-tab">
            <h2>SESSION HISTORY</h2>
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
                      <td><code>{session.session_id}</code></td>
                      <td>{session.task}</td>
                      <td>
                        <span className="status-badge" style={{ backgroundColor: getStatusColor(session.status) }}>
                          {session.status}
                        </span>
                      </td>
                      <td>{new Date(session.started_at).toLocaleString()}</td>
                      <td>
                        {session.status === 'completed' && (
                          <button onClick={() => viewResults(session.session_id)}>View Results</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="no-sessions">
                <p>No sessions yet. Run your first task!</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'results' && selectedSession && (
          <div className="results-tab">
            <h2>RESULTS: {selectedSession.session_id}</h2>
            <div className="status-badge" style={{ backgroundColor: getStatusColor(selectedSession.status) }}>
              {selectedSession.status}
            </div>

            {selectedSession.result && (
              <>
                {selectedSession.result.summary && (
                  <div className="result-section">
                    <h3>TASK SUMMARY</h3>
                    <p>
                      Total: {selectedSession.result.summary.total} |
                      Completed: {selectedSession.result.summary.counts?.success || 0} |
                      Failed: {selectedSession.result.summary.counts?.failed || 0}
                    </p>
                    <div className="task-list">
                      {selectedSession.result.summary.tasks?.map((task) => (
                        <div key={task.id} className={`task-item ${task.status}`}>
                          <span className="task-id">{task.id}</span>
                          <span className="task-title">{task.title}</span>
                          <span className="task-agent">{task.agent}</span>
                          <span className="task-status">
                            {task.status === 'success' ? '✓' : task.status === 'failed' ? '✗' : task.status === 'running' ? '⟳' : '○'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(selectedSession.result.disabled_agents?.length > 0 || selectedSession.disabled_agents?.length > 0) && (
                  <div className="result-section">
                    <h3>DISABLED AGENTS</h3>
                    <div className="disabled-agent-list">
                      {(selectedSession.result.disabled_agents || selectedSession.disabled_agents || []).map((item) => (
                        <div key={item.agent} className="disabled-agent-item">
                          <strong>{item.agent}</strong>
                          <span>{item.reason}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {(selectedSession.result.execution_summary || selectedSession.execution_summary) && (
                  <div className="result-section">
                    <h3>EXECUTION ORDER</h3>
                    <pre>{selectedSession.result.execution_summary || selectedSession.execution_summary}</pre>
                  </div>
                )}

                {selectedSession.result.summary?.counts?.success > 0 && (
                  <div className="result-section">
                    <h3>GENERATED FILES</h3>
                    <p>📁 Project Location: flask_api/project/{selectedSession.session_id}/</p>
                  </div>
                )}

                {selectedSession.result.goal_analysis && (
                  <div className="result-section">
                    <h3>GOAL ANALYSIS</h3>
                    <pre>{JSON.stringify(selectedSession.result.goal_analysis, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.result.project_build && Object.keys(selectedSession.result.project_build).length > 0 && (
                  <div className="result-section">
                    <h3>PROJECT BUILD</h3>
                    <pre>{JSON.stringify(selectedSession.result.project_build, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.result.validation && Object.keys(selectedSession.result.validation).length > 0 && (
                  <div className="result-section">
                    <h3>VALIDATION</h3>
                    <pre>{JSON.stringify(selectedSession.result.validation, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.result.runtime && Object.keys(selectedSession.result.runtime).length > 0 && (
                  <div className="result-section">
                    <h3>RUNTIME</h3>
                    <pre>{JSON.stringify(selectedSession.result.runtime, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.result.evaluation && Object.keys(selectedSession.result.evaluation).length > 0 && (
                  <div className="result-section">
                    <h3>EVALUATION</h3>
                    <pre>{JSON.stringify(selectedSession.result.evaluation, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.result.final_review && (
                  <div className="result-section">
                    <h3>FINAL REVIEW</h3>
                    <pre>{JSON.stringify(selectedSession.result.final_review, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.result.planning_trace && (
                  <div className="result-section">
                    <h3>PLANNING TRACE</h3>
                    <pre>{JSON.stringify(selectedSession.result.planning_trace, null, 2)}</pre>
                  </div>
                )}

                {selectedSession.events && selectedSession.events.length > 0 && (
                  <div className="result-section">
                    <h3>EVENTS ({selectedSession.events.length})</h3>
                    <div className="events-list">
                      {selectedSession.events.slice(-20).map((event, idx) => (
                        <div key={idx} className="event-item">
                          <strong>{event.type}</strong>
                          <span>{JSON.stringify(event.data)?.slice(0, 100)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
