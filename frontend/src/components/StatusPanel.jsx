import TaskCards from "./TaskCards";

export default function StatusPanel({ status, result, sessionId }) {
  const normalizedStatus = status || "idle";
  const isDone = normalizedStatus === "completed" || normalizedStatus === "failed";
  const counts = result?.summary?.counts || {};
  const totalTasks = result?.summary?.total ?? 0;
  const successCount = counts.success ?? 0;
  const failedCount = counts.failed ?? 0;
  const skippedCount = counts.skipped ?? 0;
  const outputDirectory =
    result?.output_files?.project_files?.[0]?.split("/").slice(0, -1).join("/") ||
    "Not available";
  const summaryTone = normalizedStatus === "failed" ? "failure-summary" : "success-summary";
  const prettyStatus =
    normalizedStatus === "completed"
      ? "Completed"
      : normalizedStatus === "failed"
        ? "Failed"
        : normalizedStatus === "running"
          ? "Running"
          : normalizedStatus === "starting"
            ? "Starting"
            : "Idle";
  const isLoading = normalizedStatus === "running" || normalizedStatus === "starting";

  // Extract task summaries for TaskCards
  const taskSummaries = result?.tasks || [];

  // Calculate success rate
  const successRate = totalTasks > 0 ? Math.round((successCount / totalTasks) * 100) : 0;

  return (
    <section className="panel status-panel">
      <div className="panel-header">
        <h2>Session Status</h2>
        <span className={`status-chip ${normalizedStatus}`}>
          {normalizedStatus}
        </span>
      </div>

      <dl className="status-grid">
        <div>
          <dt>Session</dt>
          <dd className="session-code">{sessionId || "No session started"}</dd>
        </div>
        <div>
          <dt>State</dt>
          <dd>{result?.state || "Waiting"}</dd>
        </div>
      </dl>

      {/* Quick Stats Row */}
      {isDone && (
        <div className="stats-row">
          <div className="stat-item">
            <span className="stat-value">{totalTasks}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat-item success">
            <span className="stat-value">{successCount}</span>
            <span className="stat-label">Success</span>
          </div>
          <div className="stat-item failed">
            <span className="stat-value">{failedCount}</span>
            <span className="stat-label">Failed</span>
          </div>
          <div className="stat-item skipped">
            <span className="stat-value">{skippedCount}</span>
            <span className="stat-label">Skipped</span>
          </div>
          <div className="stat-item rate">
            <span className="stat-value">{successRate}%</span>
            <span className="stat-label">Success Rate</span>
          </div>
        </div>
      )}

      {/* Task Cards */}
      {taskSummaries.length > 0 && <TaskCards tasks={taskSummaries} />}

      <div className="result-block">
        <h3>Result Summary</h3>
        {isLoading ? (
          <div className="status-loading">
            <span className="loading-dot" />
            <p className="loading-text">Running orchestration and collecting events...</p>
          </div>
        ) : !isDone ? (
          <p className="loading-text">Waiting for orchestration to start...</p>
        ) : result ? (
          <div className={`result-summary ${summaryTone}`}>
            <p className="result-headline">
              {normalizedStatus === "completed"
                ? `✔ ${successCount} task${successCount === 1 ? "" : "s"} completed`
                : `❌ ${failedCount || 1} task${failedCount === 1 ? "" : "s"} failed`}
            </p>
            <dl className="summary-grid">
              <div>
                <dt>Status</dt>
                <dd>{prettyStatus}</dd>
              </div>
              <div>
                <dt>Output Directory</dt>
                <dd className="output-dir">{outputDirectory}</dd>
              </div>
            </dl>
            {result?.error ? <p className="result-error">{result.error}</p> : null}
          </div>
        ) : (
          <p className="empty-state">No result available.</p>
        )}
      </div>
    </section>
  );
}
