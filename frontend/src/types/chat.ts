import type { Attachment } from "../services/backend";

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  kind?: "text" | "audio";
  created_at?: string;
  attachments?: Attachment[];
}
