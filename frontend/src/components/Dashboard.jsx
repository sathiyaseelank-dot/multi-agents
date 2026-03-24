export default function Dashboard({
  task,
  onTaskChange,
  onRun,
  isRunning,
  sessionId,
}) {
  return (
    <section className="panel dashboard-panel">
      <div className="panel-header">
        <h2>Run Task</h2>
        <span className={`status-chip ${isRunning ? "running" : "idle"}`}>
          {isRunning ? "Running" : "Ready"}
        </span>
      </div>

      <label className="field-label" htmlFor="task-input">
        Task Description
      </label>
      <textarea
        id="task-input"
        className="task-input"
        rows="4"
        value={task}
        onChange={(event) => onTaskChange(event.target.value)}
        placeholder="Build a calculator with API, UI, and tests"
      />

      <div className="dashboard-actions">
        <button
          className={`run-button ${isRunning ? "is-loading" : ""}`}
          onClick={onRun}
          disabled={isRunning}
        >
          {isRunning ? "Running..." : "Run"}
        </button>
        {isRunning ? <span className="loading-pill">Orchestration in progress</span> : null}
        <div className="session-block">
          <span className="field-label">Session ID</span>
          <code>{sessionId || "No active session"}</code>
        </div>
      </div>
    </section>
  );
}
