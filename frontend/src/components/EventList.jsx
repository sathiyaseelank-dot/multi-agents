import { useEffect, useMemo, useRef } from "react";

const STATUS_CONFIG = {
  task_started: { icon: "⏳", label: "In Progress", tone: "running" },
  task_completed: { icon: "✅", label: "Done", tone: "success" },
  task_failed: { icon: "❌", label: "Failed", tone: "error" },
  phase_started: { icon: "🚀", label: "Phase Started", tone: "phase" },
  phase_completed: { icon: "📦", label: "Phase Done", tone: "phase" },
  run_started: { icon: "🏁", label: "Run Started", tone: "neutral" },
  run_completed: { icon: "🎉", label: "Completed", tone: "success" },
  run_resumed: { icon: "▶️", label: "Resumed", tone: "phase" },
  info: { icon: "ℹ️", label: "Info", tone: "neutral" },
  warning: { icon: "⚠️", label: "Warning", tone: "phase" },
  error: { icon: "🔴", label: "Error", tone: "error" },
  plan_created: { icon: "📋", label: "Plan Ready", tone: "phase" },
  agent_retry: { icon: "🔄", label: "Retrying", tone: "phase" },
};

function getEventConfig(type) {
  return STATUS_CONFIG[type] || { icon: "•", label: type, tone: "neutral" };
}

function formatTimestamp(timestamp) {
  try {
    return new Date(timestamp).toLocaleTimeString();
  } catch {
    return "";
  }
}

function formatEventDetails(data, type) {
  const parts = [];

  // Task-specific formatting
  if (type.includes("task_")) {
    if (data.task_id) parts.push(data.task_id);
    if (data.title) parts.push(data.title);
    if (data.agent) parts.push(`via ${data.agent}`);
    if (data.execution_time) parts.push(`${data.execution_time.toFixed(1)}s`);
    if (data.summary) parts.push(data.summary);
    if (data.error) parts.push(data.error);
  }

  // Phase-specific formatting
  if (type.includes("phase_")) {
    if (data.phase) parts.push(`Phase ${data.phase}/${data.total_phases}`);
    if (data.mode) parts.push(`(${data.mode})`);
    if (data.task_count) parts.push(`${data.task_count} task(s)`);
    if (data.counts) {
      const c = data.counts;
      if (c.success !== undefined) parts.push(`✓ ${c.success}`);
      if (c.failed !== undefined) parts.push(`✗ ${c.failed}`);
      if (c.skipped !== undefined) parts.push(`⊘ ${c.skipped}`);
    }
  }

  // Run-level events
  if (type.includes("run_")) {
    if (data.task) parts.push(`"${data.task}"`);
    if (data.session_id) parts.push(`Session: ${data.session_id}`);
    if (data.completed !== undefined) parts.push(`${data.completed} completed`);
    if (data.pending !== undefined) parts.push(`${data.pending} pending`);
  }

  // Plan created
  if (type === "plan_created") {
    if (data.epic) parts.push(data.epic);
    if (data.task_count) parts.push(`${data.task_count} tasks`);
    if (data.phase_count) parts.push(`${data.phase_count} phases`);
  }

  // Agent retry
  if (type === "agent_retry") {
    if (data.task_id) parts.push(data.task_id);
    if (data.original_agent) parts.push(`${data.original_agent} → ${data.fallback_agent}`);
    if (data.reason) parts.push(data.reason);
  }

  // Info/warning/error
  if (["info", "warning", "error"].includes(type)) {
    if (data.message) parts.push(data.message);
    if (data.detail) parts.push(data.detail);
  }

  return parts.join(" • ") || "No details";
}

export default function EventList({ events }) {
  const bottomRef = useRef(null);
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => {
      if (typeof a.seq === "number" && typeof b.seq === "number") {
        return a.seq - b.seq;
      }
      return new Date(a.timestamp) - new Date(b.timestamp);
    });
  }, [events]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sortedEvents]);

  return (
    <section className="panel event-panel">
      <div className="panel-header">
        <h2>Live Events</h2>
        <span className="event-count">{events.length} events</span>
      </div>

      <div className="event-list">
        {sortedEvents.length === 0 ? (
          <p className="empty-state">No events yet. Start a run to see activity.</p>
        ) : (
          sortedEvents.map((event, index) => {
            const config = getEventConfig(event.type);
            return (
              <article
                key={`${event.seq ?? event.timestamp}-${event.type}-${index}`}
                className={`event-card ${config.tone}`}
              >
                <div className="event-header">
                  <div className="event-title">
                    <span className="event-icon">{config.icon}</span>
                    <strong>{config.label}</strong>
                  </div>
                  <time className="event-time">
                    {formatTimestamp(event.timestamp)}
                  </time>
                </div>
                <p className="event-details">{formatEventDetails(event.data || {}, event.type)}</p>
              </article>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
