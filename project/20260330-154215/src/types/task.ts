export type TaskStatus = 
  | 'pending'
  | 'planning'
  | 'running'
  | 'completed'
  | 'failed';

export interface Task {
  id: string;
  description: string;
  status: TaskStatus;
  agent?: string;
  progress?: number;
  error?: string;
  result?: string;
  createdAt: string;
  updatedAt: string;
  dependencies?: string[];
}

export interface TaskResult {
  taskId: string;
  output: string;
  files: string[];
  duration: number;
}
