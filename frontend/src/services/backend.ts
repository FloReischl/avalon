const BACKEND_BASE_URL = "http://127.0.0.1:8095";

export interface BackendHealth {
  status: "ok";
  service: string;
}

export interface ChatStreamHandlers {
  onChunk: (text: string) => void;
}

interface ChatChunkData {
  text: string;
}

export async function getBackendHealth(): Promise<BackendHealth> {
  const response = await fetch(`${BACKEND_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Backend health check failed with ${response.status}`);
  }
  return response.json() as Promise<BackendHealth>;
}

export async function streamChatMessage(
  message: string,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Chat request failed with ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Chat response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const rawEvent of events) {
      const lines = rawEvent.split("\n");
      const event = lines
        .find((line) => line.startsWith("event: "))
        ?.slice("event: ".length);
      const data = lines
        .find((line) => line.startsWith("data: "))
        ?.slice("data: ".length);

      if (!event || data === undefined) {
        throw new Error("Invalid chat stream event");
      }

      if (event === "chunk") {
        const parsed = JSON.parse(data) as Partial<ChatChunkData>;
        if (typeof parsed.text !== "string") {
          throw new Error("Invalid chat stream chunk");
        }

        handlers.onChunk(parsed.text);
        continue;
      }

      if (event === "done") {
        completed = true;
        return;
      }

      if (event === "error") {
        throw new Error("Chat generation failed");
      }

      throw new Error(`Unknown chat stream event: ${event}`);
    }

    if (done) {
      break;
    }
  }

  if (!completed) {
    throw new Error("Chat stream ended without done event");
  }
}

