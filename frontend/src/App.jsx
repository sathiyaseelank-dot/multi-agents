import { useState, useEffect, useRef } from 'react';
import './styles.css';

const API_BASE = 'http://localhost:5000/api/orchestrator';

const EVENT_TYPE_LABELS = {
  run_started: 'Run started',
  run_completed: 'Run completed',
  plan_created: 'Plan ready',
  phase_started: 'Phase started',
  phase_completed: 'Phase completed',
  task_started: 'Task started',
  task_completed: 'Task completed',
  task_failed: 'Task failed',
  agent_retry: 'Retrying with fallback agent',
  info: 'Info',
  warning: 'Warning',
  error: 'Error',
};

function sortEvents(events = []) {
  return [...events].sort((a, b) => {
    if (typeof a.seq === 'number' && typeof b.seq === 'number') {
      return a.seq - b.seq;
    }
    return new Date(a.timestamp) - new Date(b.timestamp);
  });
}

function toSentenceCase(value) {
  if (!value) return '';
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatEventSummary(event) {
  const data = event?.data || {};

  switch (event?.type) {
    case 'run_started':
      return data.task || 'Starting orchestration';
    case 'plan_created':
      return data.execution_summary || `${data.phase_count || 0} phases planned`;
    case 'phase_started':
      return `Phase ${data.phase}/${data.total_phases} (${data.mode || 'sequential'}) with ${data.task_count || 0} task(s)`;
    case 'phase_completed':
      return `Phase ${data.phase}/${data.total_phases} finished`;
    case 'task_started':
      return `${data.task_id}: ${data.title}${data.agent ? ` via ${data.agent}` : ''}`;
    case 'task_completed':
      return `${data.task_id}: ${data.summary || data.title || 'Completed'}`;
    case 'task_failed':
      return `${data.task_id}: ${data.error || 'Failed'}`;
    case 'agent_retry':
      return `${data.task_id}: ${data.original_agent} -> ${data.fallback_agent}`;
    case 'info':
    case 'warning':
    case 'error':
      return data.message || data.detail || 'No details';
    default:
      return JSON.stringify(data);
  }
}

function buildExecutionView(events = []) {
  const sorted = sortEvents(events);
  const phases = [];
  const tasks = [];
  let planEvent = null;
  let currentPhase = null;
  let currentTask = null;

  sorted.forEach((event) => {
    const data = event.data || {};

    if (event.type === 'plan_created') {
      planEvent = event;
    }

    if (event.type === 'phase_started') {
      currentPhase = {
        phase: data.phase,
        totalPhases: data.total_phases,
        mode: data.mode,
        taskIds: data.task_ids || [],
      };
      phases.push({
        id: `phase-${data.phase}`,
        phase: data.phase,
        title: `Phase ${data.phase}`,
        description: data.task_ids?.length
          ? `Tasks: ${data.task_ids.join(', ')}`
          : 'Work started',
        status: 'running',
      });
    }

    if (event.type === 'phase_completed') {
      const existing = phases.find((phase) => phase.phase === data.phase);
      const counts = data.counts || {};
      const description = `Completed ${counts.success || 0} success, ${counts.failed || 0} failed, ${counts.skipped || 0} skipped`;
      if (existing) {
        existing.status = 'completed';
        existing.description = description;
      } else {
        phases.push({
          id: `phase-${data.phase}`,
          phase: data.phase,
          title: `Phase ${data.phase}`,
          description,
          status: 'completed',
        });
      }
      if (currentPhase?.phase === data.phase) {
        currentPhase = null;
      }
    }

    if (event.type === 'task_started') {
      currentTask = {
        id: data.task_id,
        title: data.title,
        agent: data.agent,
      };
      tasks.push({
        id: data.task_id,
        title: data.title,
        detail: data.agent ? `Doing now via ${data.agent}` : 'Doing now',
        status: 'running',
      });
    }

    if (event.type === 'task_completed' || event.type === 'task_failed') {
      const existing = tasks.find((task) => task.id === data.task_id);
      const status = event.type === 'task_completed' ? 'completed' : 'failed';
      const detail =
        event.type === 'task_completed'
          ? data.summary || 'Finished'
          : data.error || 'Failed';
      if (existing) {
        existing.status = status;
        existing.detail = detail;
      } else {
        tasks.push({
          id: data.task_id,
          title: data.title || data.task_id,
          detail,
          status,
        });
      }
      if (currentTask?.id === data.task_id) {
        currentTask = null;
      }
    }
  });

  if (planEvent?.data?.plan?.phases?.length) {
    const phaseStatuses = new Map(phases.map((phase) => [phase.phase, phase]));
    planEvent.data.plan.phases.forEach((phase) => {
      if (!phaseStatuses.has(phase.phase)) {
        phases.push({
          id: `phase-${phase.phase}`,
          phase: phase.phase,
          title: `Phase ${phase.phase}`,
          description: phase.description || `Tasks: ${(phase.task_ids || []).join(', ')}`,
          status: 'pending',
        });
      } else {
        const existing = phaseStatuses.get(phase.phase);
        if (existing.status === 'pending' || existing.description?.startsWith('Tasks:')) {
          existing.description = phase.description || existing.description;
        }
      }
    });
    phases.sort((a, b) => a.phase - b.phase);
  }

  const latestEvent = sorted[sorted.length - 1];
  const completedTasks = tasks.filter((task) => task.status === 'completed').slice(-4).reverse();
  const failedTasks = tasks.filter((task) => task.status === 'failed').slice(-2).reverse();

  const currentMessage = currentTask
    ? `${currentTask.title}${currentTask.agent ? ` via ${currentTask.agent}` : ''}`
    : currentPhase
      ? `Phase ${currentPhase.phase}/${currentPhase.totalPhases} is in progress`
      : latestEvent
        ? formatEventSummary(latestEvent)
        : 'Waiting for orchestration to start';

  return {
    latestEvent,
    planEvent,
    currentMessage,
    currentPhase,
    completedTasks,
    failedTasks,
    phases,
    recentEvents: sorted.slice(-8),
  };
}

function App() {
  const [task, setTask] = useState('');
  const [sessions, setSessions] = useState([]);
  const [runningSession, setRunningSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  const [activeTab, setActiveTab] = useState('run');
  const eventsEndRef = useRef(null);
  const pollTimeoutRef = useRef(null);
  const activePollSessionRef = useRef(null);

  const stopPolling = () => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  // Fetch sessions on mount and every 5 seconds
  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000);
    return () => {
      clearInterval(interval);
      stopPolling();
    };
  }, []);

  useEffect(() => {
    if (runningSession?.session_id) {
      return;
    }

    const latestActiveSession = sessions.find((session) =>
      ['running', 'pending', 'starting', 'started', 'incomplete'].includes(session.status)
    );

    if (latestActiveSession?.session_id) {
      setRunningSession((current) => current ?? latestActiveSession);
      pollStatus(latestActiveSession.session_id);
    }
  }, [sessions, runningSession?.session_id]);

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
    stopPolling();
    activePollSessionRef.current = sessionId;

    const poll = async () => {
      if (activePollSessionRef.current !== sessionId) {
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/status/${sessionId}`);
        const data = await response.json();

        if (response.ok && ['pending', 'starting', 'started', 'running'].includes(data.status)) {
          setRunningSession(data);
          pollTimeoutRef.current = setTimeout(poll, 3000);
        } else if (response.status === 404) {
          pollTimeoutRef.current = setTimeout(poll, 3000);
        } else {
          setRunningSession(data);
          activePollSessionRef.current = null;
          fetchSessions();
        }
      } catch (error) {
        console.error('Failed to poll status:', error);
        pollTimeoutRef.current = setTimeout(poll, 3000);
      }
    };
    poll();
  };

  const viewResults = async (sessionId) => {
    stopPolling();
    activePollSessionRef.current = null;
    try {
      const response = await fetch(`${API_BASE}/results/${sessionId}`);
      const data = await response.json();
      setSelectedSession(data);
      setActiveTab('results');
    } catch (error) {
      console.error('Failed to fetch results:', error);
    }
  };

  const viewStatus = (session) => {
    setRunningSession(session);
    setActiveTab('status');
    pollStatus(session.session_id);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#22c55e';
      case 'running': return '#3b82f6';
      case 'failed': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const executionView = buildExecutionView(runningSession?.events || []);
  const planData = executionView.planEvent?.data?.plan;
  const executionSummary = executionView.planEvent?.data?.execution_summary;

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [executionView.recentEvents.length]);

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
                    <p>{executionView.currentMessage || 'Executing task... This may take 2-5 minutes'}</p>
                  </div>
                )}
                {executionView.phases.length > 0 && (
                  <div className="status-section">
                    <h3>Execution Plan</h3>
                    <div className="phase-list">
                      {executionView.phases.map((phase) => (
                        <div key={phase.id} className={`phase-item ${phase.status}`}>
                          <div className="phase-title-row">
                            <span className="phase-title">{phase.title}</span>
                            <span className={`phase-status ${phase.status}`}>
                              {phase.status === 'running'
                                ? 'Doing'
                                : phase.status === 'completed'
                                  ? 'Done'
                                  : phase.status === 'failed'
                                    ? 'Failed'
                                    : 'Pending'}
                            </span>
                          </div>
                          <p className="phase-description">{phase.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {planData && (
                  <div className="status-section">
                    <h3>Planner Output</h3>
                    {planData.epic && (
                      <div className="planner-block">
                        <div className="planner-label">Epic</div>
                        <p className="planner-copy">{planData.epic}</p>
                      </div>
                    )}
                    {planData.tasks?.length > 0 && (
                      <div className="planner-block">
                        <div className="planner-label">Tasks</div>
                        <div className="planner-rows">
                          {planData.tasks.map((item) => (
                            <div key={item.id} className="planner-row">
                              <div className="planner-row-main">
                                <span className="planner-id">{item.id}</span>
                                <span className="planner-title">{item.title}</span>
                              </div>
                              <div className="planner-meta">
                                <span>{item.agent}</span>
                                <span>{item.type}</span>
                                {item.dependencies?.length > 0 && (
                                  <span>{`depends on ${item.dependencies.join(', ')}`}</span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {planData.phases?.length > 0 && (
                      <div className="planner-block">
                        <div className="planner-label">Phases</div>
                        <div className="planner-rows">
                          {planData.phases.map((phase) => (
                            <div key={phase.phase} className="planner-row">
                              <div className="planner-row-main">
                                <span className="planner-title">
                                  {`Phase ${phase.phase} (${phase.parallel ? 'parallel' : 'sequential'})`}
                                </span>
                              </div>
                              <div className="planner-copy">{phase.description}</div>
                              <div className="planner-meta">
                                <span>{`Tasks: ${(phase.task_ids || []).join(', ')}`}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {executionSummary && (
                      <div className="planner-block">
                        <div className="planner-label">Computed Execution Order</div>
                        <pre className="planner-pre">{executionSummary}</pre>
                      </div>
                    )}
                  </div>
                )}
                {(executionView.completedTasks.length > 0 || executionView.failedTasks.length > 0 || executionView.currentPhase) && (
                  <div className="status-section">
                    <h3>What The Orchestrator Is Doing</h3>
                    <div className="progress-list">
                      {executionView.currentPhase && (
                        <div className="progress-item doing">
                          <span className="progress-label">Doing</span>
                          <span className="progress-text">
                            {`Phase ${executionView.currentPhase.phase}/${executionView.currentPhase.totalPhases} is active`}
                          </span>
                        </div>
                      )}
                      {executionView.completedTasks.map((task) => (
                        <div key={task.id} className="progress-item done">
                          <span className="progress-label">Done</span>
                          <span className="progress-text">{`${task.id}: ${task.title}`}</span>
                        </div>
                      ))}
                      {executionView.failedTasks.map((task) => (
                        <div key={task.id} className="progress-item failed">
                          <span className="progress-label">Failed</span>
                          <span className="progress-text">{`${task.id}: ${task.title}`}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {runningSession.events && runningSession.events.length > 0 && (
                  <div className="events">
                    <h3>Recent Orchestration Updates</h3>
                    <div className="events-list">
                      {executionView.recentEvents.map((event, idx) => (
                        <div key={idx} className="event-item">
                          <span className="event-type">{EVENT_TYPE_LABELS[event.type] || toSentenceCase(event.type.replaceAll('_', ' '))}</span>
                          <span className="event-data">{formatEventSummary(event)}</span>
                        </div>
                      ))}
                      <div ref={eventsEndRef} />
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
                        {session.status !== 'completed' && (
                          <button
                            className="small"
                            onClick={() => viewStatus(session)}
                          >
                            View Status
                          </button>
                        )}
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
