export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  kind?: "text" | "audio";
}
