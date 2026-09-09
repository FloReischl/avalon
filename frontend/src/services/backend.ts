const BACKEND_BASE_URL = "http://127.0.0.1:8095";

export interface BackendHealth {
  status: "ok";
  service: string;
}

export interface ChatStreamRequest {
  chatId?: number;
  message: string;
}

export interface ChatStreamHandlers {
  onChat?: (chatId: number) => void;
  onChunk: (text: string) => void;
  onTranscriptChunk?: (text: string) => void;
  onTranscriptError?: () => void;
  onDone?: () => void;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSummary {
  id: number;
  title: string;
  pinned: boolean;
  created_at: string;
}


export interface PersistentMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatDetail extends ChatSummary {
  messages: PersistentMessage[];
}

export interface TtsResponse {
  playbackId: string;
  response: Response;
}

interface ChatChunkData {
  text: string;
}

interface ChatEventData {
  id: string;
}

export async function getBackendHealth(): Promise<BackendHealth> {
  const response = await fetch(`${BACKEND_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Backend health check failed with ${response.status}`);
  }
  return response.json() as Promise<BackendHealth>;
}

export async function getChats(): Promise<ChatSummary[]> {
  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/chats`);
  if (!response.ok) {
    throw new Error(`Chat list request failed with ${response.status}`);
  }

  return response.json() as Promise<ChatSummary[]>;
}

export async function getChat(chatId: number): Promise<ChatDetail> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/chats/${chatId}`,
  );
  if (!response.ok) {
    throw new Error(`Chat request failed with ${response.status}`);
  }

  return response.json() as Promise<ChatDetail>;
}

export async function renameChat(
  chatId: number,
  title: string,
): Promise<ChatSummary> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/chats/${chatId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    },
  );

  if (!response.ok) {
    throw new Error(`Chat rename request failed with ${response.status}`);
  }

  return response.json() as Promise<ChatSummary>;
}

export async function setChatPinned(
  chatId: number,
  pinned: boolean,
): Promise<ChatSummary> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/chats/${chatId}/pinned`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ pinned }),
    },
  );

  if (!response.ok) {
    throw new Error(`Chat pin request failed with ${response.status}`);
  }

  return response.json() as Promise<ChatSummary>;
}

export async function deleteChat(
  chatId: number,
): Promise<void> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/chats/${chatId}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw new Error(`Chat delete request failed with ${response.status}`);
  }
}

export async function streamChatMessage(

  request: ChatStreamRequest,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const body = request.chatId === undefined
    ? { message: request.message }
    : {
        chat_id: request.chatId,
        message: request.message,
      };

  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });

  await consumeChatStream(response, handlers);
}

export async function startAudioRecording(): Promise<void> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/audio/recording/start`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Audio recording start failed with ${response.status}`);
  }
}

export async function abortAudioRecording(): Promise<void> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/audio/recording/abort`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Audio recording abort failed with ${response.status}`);
  }
}

export async function streamAudioResponse(
  messages: ConversationMessage[],
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
  chatId?: number,
): Promise<void> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/audio/recording/stop`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        chatId === undefined
          ? { messages }
          : { chat_id: chatId, messages },
      ),
      signal,
    },
  );

  await consumeChatStream(response, handlers);
}

export async function streamDialogResponse(
  messages: ConversationMessage[],
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
  chatId?: number,
): Promise<void> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/audio/dialog/turn`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        chatId === undefined
          ? { messages }
          : { chat_id: chatId, messages },
      ),
      signal,
    },
  );

  await consumeChatStream(response, handlers);
}

export async function synthesizeSpeech(
  text: string,
  signal: AbortSignal,
): Promise<TtsResponse> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/tts`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
      signal,
    },
  );

  if (!response.ok) {
    throw new Error(`TTS request failed with ${response.status}`);
  }

  const playbackId = response.headers.get(
    "X-Avalo-TTS-Playback-ID",
  );
  if (!playbackId) {
    throw new Error("TTS response has no playback ID");
  }

  return {
    playbackId,
    response,
  };
}

export async function notifyTtsPlaybackEnded(
  playbackId: string,
): Promise<void> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/tts/playback-ended`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        playback_id: playbackId,
      }),
    },
  );

  if (!response.ok) {
    throw new Error(
      `TTS playback notification failed with ${response.status}`,
    );
  }
}

async function consumeChatStream(
  response: Response,
  handlers: ChatStreamHandlers,
): Promise<void> {
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

      if (event === "chat") {
        const parsed = JSON.parse(data) as Partial<ChatEventData>;
        const chatId = Number(parsed.id);

        if (!Number.isInteger(chatId) || chatId <= 0) {
          throw new Error("Invalid chat stream chat ID");
        }

        handlers.onChat?.(chatId);
        continue;
      }

      if (event === "chunk") {
        const parsed = JSON.parse(data) as Partial<ChatChunkData>;
        if (typeof parsed.text !== "string") {
          throw new Error("Invalid chat stream chunk");
        }

        handlers.onChunk(parsed.text);
        continue;
      }

      if (event === "transcript_chunk") {
        const parsed = JSON.parse(data) as Partial<ChatChunkData>;
        if (typeof parsed.text !== "string") {
          throw new Error("Invalid chat stream transcript chunk");
        }

        handlers.onTranscriptChunk?.(parsed.text);
        continue;
      }

      if (event === "transcript_error") {
        handlers.onTranscriptError?.();
        continue;
      }

      if (event === "done") {
        completed = true;
        handlers.onDone?.();
        continue;
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