import type { Attachment, WorkflowExecution } from "../services/backend";

export interface ChatMessage {
  id?: number;
  kind?: "text" | "progress" | "audio";
  role: "user" | "assistant";
  content: string;
  created_at?: string;
  attachments?: Attachment[];
  progress_messages?: string[];
  workflow_execution?: WorkflowExecution;
}
