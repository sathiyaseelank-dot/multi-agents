import React, { useState } from 'react';
import './TaskForm.css';

interface TaskFormProps {
  onSubmit: (description: string) => void;
  onCancel: () => void;
}

export const TaskForm: React.FC<TaskFormProps> = ({ onSubmit, onCancel }) => {
  const [description, setDescription] = useState('');
  const [agent, setAgent] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (description.trim()) {
      onSubmit(description.trim());
    }
  };

  return (
    <div className="modal-overlay">
      <div className="task-form-modal">
        <h2>Create New Task</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="description">Task Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what you want to build..."
              rows={4}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="agent">Agent (Optional)</label>
            <select
              id="agent"
              value={agent}
              onChange={(e) => setAgent(e.target.value)}
            >
              <option value="">Auto-select</option>
              <option value="codex">Codex (Planner)</option>
              <option value="opencode">OpenCode (Backend)</option>
              <option value="gemini">Gemini (Frontend)</option>
              <option value="kilo">Kilo (Testing)</option>
            </select>
          </div>

          <div className="form-actions">
            <button 
              type="button" 
              className="btn-secondary"
              onClick={onCancel}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary"
              disabled={!description.trim()}
            >
              Create Task
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
