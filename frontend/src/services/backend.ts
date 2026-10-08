export const BACKEND_BASE_URL = "http://127.0.0.1:8095";

let agentBearerToken: string | undefined;

export function setAgentBearerToken(token: string): void {
  if (!token) throw new Error("UI config returned an empty agent bearer token");
  agentBearerToken = token;
}

function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  if (!agentBearerToken) throw new Error("Agent bearer token is not initialized");
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${agentBearerToken}`);
  return fetch(input, { ...init, headers });
}

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
  onProcessing?: () => void;
  onChunk: (text: string) => void;
  onTranscriptChunk?: (text: string) => void;
  onTranscriptError?: () => void;
  onDone?: () => void;
}

export interface AuthorizationRequest {
  id: string;
  context: string;
  key: string;
  items: string[];
  validityType: "permanent" | "duration" | "range";
  defaultExpiry: number;
}

export interface PendingAuthorizationRequest extends AuthorizationRequest {
  sourceLabel: string;
}

export interface ProactivePermission {
  id: number;
  context: string;
  key: string;
  validityType: "permanent" | "duration" | "range";
  defaultExpiry: number;
  grant?: { id: number; expiresAt: string } | null;
  readOnly: boolean;
}

export type WorkflowConfirmationColumn = {
  key: string;
  type: "str" | "int" | "float" | "bool" | "date" | "datetime";
  nullable: boolean;
  editable: boolean;
  visible: boolean;
  label?: string;
};

export interface PendingWorkflowConfirmation {
  id: string;
  executionId: number;
  schema: { title: string; columns: WorkflowConfirmationColumn[] };
  rows: Array<Record<string, unknown>>;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSummary {
  id: number;
  title: string;
  pinned: boolean;
  agent_id: number;
  agent_name: string | null;
  created_at: string;
}


export interface TextMessage {
  id: number;
  kind: "text";
  role: "user" | "assistant";
  content: string;
  created_at: string;
  attachments: Attachment[];
}

export interface ProgressMessage {
  id: number;
  kind: "progress";
  created_at: string;
  updated_at: string;
  messages: string[];
  workflow_execution: WorkflowExecution;
}

export type PersistentMessage = TextMessage | ProgressMessage;

export interface WorkflowExecution {
  id: number;
  workflow_key: string;
  state: "running" | "pending" | "completed" | "failed" | "aborted";
}

export interface Attachment {
  id: number;
  original_file_name: string;
  mime_type: string;
  size: number;
  created_at: string;
}

export interface ChatDetail extends ChatSummary {
  messages: PersistentMessage[];
  compression_error_code?: string | null;
}

export async function loadAgentBearerToken(agentId: number): Promise<string> {
  const response = await fetch(
    `${BACKEND_BASE_URL}/api/v1/ui/token?agent_id=${encodeURIComponent(String(agentId))}`,
  );
  if (!response.ok) {
    throw new Error(`Failed to load agent bearer token: ${response.status}`);
  }
  const payload = await response.json() as { agentBearerToken?: unknown };
  if (typeof payload.agentBearerToken !== "string" || !payload.agentBearerToken) {
    throw new Error("Agent token response is invalid");
  }
  return payload.agentBearerToken;
}

export interface TtsResponse {
  playbackId: string;
  response: Response;
}

export interface AudioCallStatus {
  active: boolean;
  chat_id: number | null;
  turn_active: boolean;
  pending_speech: string | null;
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

export async function warmUpRuntime(): Promise<void> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/runtime/warm-up`,
    { method: "POST" },
  );

  if (!response.ok) {
    throw new Error(`Runtime warm-up failed with ${response.status}`);
  }
}

export async function getChats(): Promise<ChatSummary[]> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/chats`);
  if (!response.ok) {
    throw new Error(`Chat list request failed with ${response.status}`);
  }

  return response.json() as Promise<ChatSummary[]>;
}

export async function getChat(chatId: number): Promise<ChatDetail> {
  const response = await authenticatedFetch(
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
  const response = await authenticatedFetch(
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
  const response = await authenticatedFetch(
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
  const response = await authenticatedFetch(
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

  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });

  await consumeChatStream(response, handlers);
}

export async function confirmAuthorization(
  requestId: string, approvedItemIndexes: number[], durationSeconds?: number,
): Promise<void> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/authorization-requests/${requestId}/confirm`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approved_item_indexes: approvedItemIndexes, duration_seconds: durationSeconds }) },
  );
  if (!response.ok) throw new Error(`Authorization confirmation failed with ${response.status}`);
}

export async function abortAuthorization(requestId: string): Promise<void> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/authorization-requests/${requestId}/abort`,
    { method: "POST" },
  );
  if (!response.ok) throw new Error(`Authorization abort failed with ${response.status}`);
}

function workflowConfirmationFromPayload(payload: Record<string, unknown>): PendingWorkflowConfirmation {
  const schema = payload.schema as Record<string, unknown>;
  if (!schema || typeof schema.title !== "string" || !Array.isArray(schema.columns) || !Array.isArray(payload.rows)) {
    throw new Error("Workflow confirmation response is invalid");
  }
  return {
    id: String(payload.id), executionId: Number(payload.execution_id),
    schema: { title: schema.title, columns: schema.columns as WorkflowConfirmationColumn[] },
    rows: payload.rows as Array<Record<string, unknown>>,
  };
}

export async function getPendingWorkflowConfirmation(): Promise<PendingWorkflowConfirmation | null> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/workflow-executions/confirmations/pending`);
  if (!response.ok) throw new Error(`Workflow confirmation request failed with ${response.status}`);
  const payload = await response.json() as Record<string, unknown> | null;
  return payload === null ? null : workflowConfirmationFromPayload(payload);
}

export async function confirmWorkflowConfirmation(id: string, rows: Array<Record<string, unknown>>): Promise<void> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/workflow-executions/confirmations/${encodeURIComponent(id)}/confirm`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ rows }) },
  );
  if (!response.ok) throw new Error(`Workflow confirmation submit failed with ${response.status}`);
}

export async function cancelWorkflowConfirmation(id: string): Promise<void> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/workflow-executions/confirmations/${encodeURIComponent(id)}/cancel`,
    { method: "POST" },
  );
  if (!response.ok) throw new Error(`Workflow confirmation cancel failed with ${response.status}`);
}

export async function getPendingAuthorizationRequests(): Promise<PendingAuthorizationRequest[]> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/authorization-requests`);
  if (!response.ok) throw new Error(`Authorization request list failed with ${response.status}`);
  const payload = await response.json() as Array<Record<string, unknown>>;
  return payload.map((request) => ({
    id: String(request.id), context: String(request.context), key: String(request.key),
    items: request.items as string[], validityType: request.validity_type as PendingAuthorizationRequest["validityType"],
    defaultExpiry: Number(request.default_expiry), sourceLabel: String(request.source_label),
  }));
}

function proactivePermissionFromPayload(permission: Record<string, unknown>): ProactivePermission {
  const grant = permission.grant as Record<string, unknown> | null;
  return {
    id: Number(permission.id), context: String(permission.context), key: String(permission.key),
    validityType: permission.validity_type as ProactivePermission["validityType"],
    defaultExpiry: Number(permission.default_expiry), readOnly: Boolean(permission.read_only),
    grant: grant ? { id: Number(grant.id), expiresAt: String(grant.expires_at) } : null,
  };
}

export async function getChatPermissions(chatId: number): Promise<ProactivePermission[]> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/chats/${chatId}/permissions`);
  if (!response.ok) throw new Error(`Chat permissions request failed with ${response.status}`);
  return (await response.json() as Array<Record<string, unknown>>).map(proactivePermissionFromPayload);
}

export async function saveChatPermission(
  chatId: number, permissionId: number, granted: boolean, expiresAt?: string,
): Promise<ProactivePermission> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/chats/${chatId}/permissions/${permissionId}`,
    { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ granted, expires_at: expiresAt }) },
  );
  if (!response.ok) throw new Error(`Chat permission update failed with ${response.status}`);
  return proactivePermissionFromPayload(await response.json() as Record<string, unknown>);
}

export async function startAudioRecording(): Promise<void> {
  const response = await authenticatedFetch(
    `${BACKEND_BASE_URL}/api/v1/audio/recording/start`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw new Error(`Audio recording start failed with ${response.status}`);
  }
}

export async function abortAudioRecording(): Promise<void> {
  const response = await authenticatedFetch(
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
  const response = await authenticatedFetch(
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
  const response = await authenticatedFetch(
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

export async function startAudioCall(chatId?: number): Promise<AudioCallStatus> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/audio/call/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chatId === undefined ? {} : { chat_id: chatId }),
  });
  if (!response.ok) throw new Error(`Audio call start failed with ${response.status}`);
  return response.json() as Promise<AudioCallStatus>;
}

export async function getAudioCallStatus(signal?: AbortSignal): Promise<AudioCallStatus> {
  const url = `${BACKEND_BASE_URL}/api/v1/audio/call/status`;
  const started = performance.now();

  console.debug("[audio-status] GET start", { url });

  try {
    const response = await authenticatedFetch(url, { signal });

    console.debug("[audio-status] GET response", {
      url,
      status: response.status,
      elapsedMs: Math.round(performance.now() - started),
    });

    if (!response.ok) {
      throw new Error(`Audio call status failed with ${response.status}`);
    }

    return await response.json() as AudioCallStatus;
  } catch (error) {
    if (signal?.aborted) {
      throw error;
    }
    console.error("[audio-status] GET failed", {
      url,
      elapsedMs: Math.round(performance.now() - started),
      error,
    });
    throw error;
  }
}

export async function consumeAudioCallSpeech(signal?: AbortSignal): Promise<string | null> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/audio/call/speech/consume`, {
    method: "POST",
    signal,
  });
  if (!response.ok) throw new Error(`Audio call speech consume failed with ${response.status}`);
  return (await response.json() as { text: string | null }).text;
}

export async function endAudioCall(): Promise<AudioCallStatus> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/audio/call/end`, { method: "POST" });
  if (!response.ok) throw new Error(`Audio call end failed with ${response.status}`);
  return response.json() as Promise<AudioCallStatus>;
}

export async function completeAudioCallTurn(): Promise<AudioCallStatus> {
  const response = await authenticatedFetch(`${BACKEND_BASE_URL}/api/v1/audio/call/turn/complete`, { method: "POST" });
  if (!response.ok) throw new Error(`Audio call turn completion failed with ${response.status}`);
  return response.json() as Promise<AudioCallStatus>;
}

export async function synthesizeSpeech(
  text: string,
  signal: AbortSignal,
): Promise<TtsResponse> {
  const response = await authenticatedFetch(
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
    "X-Avalon-TTS-Playback-ID",
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
  const response = await authenticatedFetch(
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

      if (event === "processing") {
        if (data !== "{}") {
          throw new Error("Invalid chat stream processing event");
        }

        handlers.onProcessing?.();
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
        const parsed = JSON.parse(data) as { code?: unknown };
        const code = typeof parsed.code === "string" ? parsed.code : "ChatGenerationFailed";
        throw new Error(`Chat generation failed: ${code}`);
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
