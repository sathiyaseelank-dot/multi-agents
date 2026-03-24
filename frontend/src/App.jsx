import { useEffect, useRef, useState } from "react";
import Dashboard from "./components/Dashboard";
import EventList from "./components/EventList";
import StatusPanel from "./components/StatusPanel";
import { fetchEvents, fetchSession, startRun } from "./api";

const POLL_INTERVAL_MS = 1500;

export default function App() {
  const [task, setTask] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const eventsIntervalRef = useRef(null);
  const statusIntervalRef = useRef(null);

  function stopPolling() {
    if (eventsIntervalRef.current) {
      window.clearInterval(eventsIntervalRef.current);
      eventsIntervalRef.current = null;
    }
    if (statusIntervalRef.current) {
      window.clearInterval(statusIntervalRef.current);
      statusIntervalRef.current = null;
    }
  }

  useEffect(() => {
    if (!sessionId) {
      stopPolling();
      return undefined;
    }

    let cancelled = false;

    stopPolling();

    async function pollEvents() {
      try {
        const nextEvents = await fetchEvents(sessionId);
        if (cancelled) {
          return;
        }
        setEvents(nextEvents);
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError.message);
        }
      }
    }

    async function pollStatus() {
      try {
        const session = await fetchSession(sessionId);
        if (cancelled) {
          return;
        }

        setStatus(session.status);
        setResult(session.result);
        if (session.status === "failed" && session.result?.error) {
          setError(session.result.error);
        }
        if (session.status === "completed" || session.status === "failed") {
          stopPolling();
        }
      } catch (pollError) {
        if (!cancelled) {
          setError(pollError.message);
          stopPolling();
        }
      }
    }

    pollEvents();
    pollStatus();
    eventsIntervalRef.current = window.setInterval(pollEvents, POLL_INTERVAL_MS);
    statusIntervalRef.current = window.setInterval(pollStatus, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [sessionId]);

  async function handleRun() {
    const trimmedTask = task.trim();
    if (!trimmedTask) {
      setError("Task is required.");
      return;
    }

    setIsStarting(true);
    setError("");
    setEvents([]);
    setResult(null);
    setStatus("starting");
    stopPolling();

    try {
      const response = await startRun(trimmedTask);
      setSessionId(response.session_id);
      setStatus("running");
    } catch (runError) {
      setStatus("failed");
      setError(runError.message);
    } finally {
      setIsStarting(false);
    }
  }

  const isRunning = status === "running" || status === "starting" || isStarting;

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Multi-Agent Orchestrator</p>
        <h1>Execution Dashboard</h1>
        <p className="hero-copy">
          Start a task, watch structured lifecycle events arrive, and inspect the
          final orchestration result from one screen.
        </p>
      </header>

      <Dashboard
        task={task}
        onTaskChange={setTask}
        onRun={handleRun}
        isRunning={isRunning}
        sessionId={sessionId}
      />

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="content-grid">
        <StatusPanel status={status} result={result} sessionId={sessionId} />
        <EventList events={events} />
      </section>
    </main>
  );
}
