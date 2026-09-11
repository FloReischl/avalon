export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  kind?: "text" | "audio";
  created_at?: string;
}
