import type { ChatResponse } from "../types/chat";

const BACKEND_BASE_URL = "http://127.0.0.1:8095";

export interface BackendHealth {
  status: "ok";
  service: string;
}

export async function getBackendHealth(): Promise<BackendHealth> {
  const response = await fetch(`${BACKEND_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Backend health check failed with ${response.status}`);
  }
  return response.json() as Promise<BackendHealth>;
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  void message;
  throw new Error("Text chat is not implemented yet.");
}

