import { useMemo } from "react";

const TASK_STATUS_CONFIG = {
  success: { icon: "✅", label: "Done", tone: "success" },
  failed: { icon: "❌", label: "Failed", tone: "error" },
  skipped: { icon: "⊘", label: "Skipped", tone: "skipped" },
  running: { icon: "⏳", label: "Running", tone: "running" },
  pending: { icon: "•", label: "Pending", tone: "pending" },
};

function getTaskStatusConfig(status) {
  return TASK_STATUS_CONFIG[status] || { icon: "•", label: status, tone: "pending" };
}

export default function TaskCards({ tasks = [] }) {
  const taskList = useMemo(() => {
    if (!tasks || tasks.length === 0) return [];
    return tasks;
  }, [tasks]);

  if (taskList.length === 0) {
    return null;
  }

  return (
    <div className="task-cards-section">
      <h3 className="section-title">Tasks</h3>
      <div className="task-cards-grid">
        {taskList.map((task) => {
          const config = getTaskStatusConfig(task.status);
          return (
            <div key={task.task_id} className={`task-card ${config.tone}`}>
              <div className="task-card-header">
                <span className="task-card-icon">{config.icon}</span>
                <span className="task-card-status">{config.label}</span>
              </div>
              <div className="task-card-body">
                <div className="task-card-id">{task.task_id}</div>
                <div className="task-card-title">{task.title}</div>
                {task.agent && (
                  <div className="task-card-meta">
                    <span className="task-card-agent">via {task.agent}</span>
                  </div>
                )}
                {task.execution_time && (
                  <div className="task-card-time">{task.execution_time.toFixed(1)}s</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
