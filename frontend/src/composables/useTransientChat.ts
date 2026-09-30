import {
  computed,
  markRaw,
  reactive,
  ref,
} from "vue";

import {
  deleteChat as deleteBackendChat,
  getChat,
  getChats,
  renameChat as renameBackendChat,
  setChatPinned as setBackendChatPinned,
  streamAudioResponse,
  streamChatMessage,
  streamDialogResponse,
  type ChatDetail,
  type ChatStreamHandlers,
  type ChatStreamRequest,
  type ChatSummary,
  type ConversationMessage,
  type PersistentMessage,
} from "../services/backend";

import type { ChatMessage } from "../types/chat";

export type ChatStreamer = (
  request: ChatStreamRequest,
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
) => Promise<void>;

export type AudioStreamer = (
  messages: ConversationMessage[],
  handlers: ChatStreamHandlers,
  signal: AbortSignal,
  chatId?: number,
) => Promise<void>;

export interface DialogTurnResult {
  assistantIndex: number;
}

export interface ChatManagementClient {
  getChats: () => Promise<ChatSummary[]>;
  getChat: (chatId: number) => Promise<ChatDetail>;
  renameChat: (
    chatId: number,
    title: string,
  ) => Promise<ChatSummary>;
  setChatPinned: (
    chatId: number,
    pinned: boolean,
  ) => Promise<ChatSummary>;
  deleteChat: (chatId: number) => Promise<void>;
}

const defaultChatManagementClient: ChatManagementClient = {
  getChats,
  getChat,
  renameChat: renameBackendChat,
  setChatPinned: setBackendChatPinned,
  deleteChat: deleteBackendChat,
};

function toChatMessage(message: PersistentMessage): ChatMessage {
  if (message.kind === "text") {
    return message;
  }
  return {
    id: message.id,
    kind: "progress",
    role: "assistant",
    content: "",
    created_at: message.created_at,
    progress_messages: message.messages,
    workflow_execution: message.workflow_execution,
  };
}

interface ChatState {

  chatId?: number;
  messages: ChatMessage[];
  input: string;
  errorMessage?: string;
  activeTurn?: ActiveTurn;
  backendPending: boolean;
  dialogProcessing: boolean;
  compressionErrorCode?: string;
}

interface ActiveTurn {
  prompt: string;
  startIndex: number;
  assistantIndex: number;
  controller: AbortController;
  kind: "text" | "audio" | "dialog";
  done: boolean;
  responding?: boolean;
}

function createChatState(
  chatId?: number,
  messages: ChatMessage[] = [],
): ChatState {
  return reactive({
    chatId,
    messages,
    input: "",
    errorMessage: undefined,
    activeTurn: undefined,
    backendPending: false,
    dialogProcessing: false,
    compressionErrorCode: undefined,
  });
}

export function useTransientChat(
  streamMessage: ChatStreamer = streamChatMessage,
  streamAudio: AudioStreamer = streamAudioResponse,
  chatManagement: ChatManagementClient = defaultChatManagementClient,
  streamDialog: AudioStreamer = streamDialogResponse,
) {

  const currentState = ref<ChatState>(createChatState());
  const chatSummaries = ref<ChatSummary[]>([]);
  const chatStates = new Map<number, ChatState>();
  const runningChatIds = reactive(new Set<number>());

  const messages = computed({
    get: () => currentState.value.messages,
    set: (value: ChatMessage[]) => {
      currentState.value.messages = value;
    },
  });

  const input = computed({
    get: () => currentState.value.input,
    set: (value: string) => {
      currentState.value.input = value;
    },
  });

  const errorMessage = computed({
    get: () => currentState.value.errorMessage,
    set: (value: string | undefined) => {
      currentState.value.errorMessage = value;
    },
  });

  const isGenerating = computed(() => {
    const turn = currentState.value.activeTurn;

    return turn !== undefined
      && !turn.done
      && (turn.kind !== "dialog" || turn.responding === true);
  });

  const isDialogResponding = computed(
    () =>
      currentState.value.activeTurn?.kind === "dialog"
      && currentState.value.activeTurn.responding === true,
  );

  const backendPending = computed(
    () => currentState.value.backendPending,
  );

  const isDialogProcessing = computed(
    () => currentState.value.dialogProcessing,
  );

  const selectedChatId = computed(
    () => currentState.value.chatId,
  );

  const isChatCompressionFailed = computed(
    () => currentState.value.compressionErrorCode
      === "chat_context_compression_failed",
  );

  function applyCompressionStatus(
    state: ChatState,
    errorCode: string | null | undefined,
  ) {
    state.compressionErrorCode = errorCode ?? undefined;
    if (state.compressionErrorCode === "chat_context_compression_failed") {
      state.errorMessage =
        "Dieser Chat kann wegen eines zu großen Kontextes nicht fortgesetzt werden.";
    }
  }

  function rollbackTurn(
    state: ChatState,
    turn: ActiveTurn,
  ) {
    state.messages.splice(turn.startIndex);
  }


  function acceptAudioChatId(
    state: ChatState,
    chatId: number,
  ) {
    if (
      state.chatId !== undefined
      && state.chatId !== chatId
    ) {
      throw new Error("Audio stream returned a different chat ID");
    }

    state.chatId = chatId;
    chatStates.set(chatId, state);
    runningChatIds.add(chatId);
  }

  function conversationContext(
    state: ChatState,
  ): ConversationMessage[] {
    return state.messages
      .filter(
        (message) =>
          message.content.length > 0
          && !(
            message.role === "user"
            && message.kind === "audio"
            && message.content === "🎤 Sprachnachricht"
          ),
      )
      .map(({ role, content }) => ({ role, content }));
  }

  async function refreshChats(
    showError = false,
    attempts = 1,
  ) {
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        chatSummaries.value = await chatManagement.getChats();

        return;
      } catch (error) {
        if (attempt < attempts) {
          await new Promise((resolve) => {
            window.setTimeout(resolve, 500);
          });
          continue;
        }

        console.error("[chat] failed to refresh chat list", error);

        if (showError) {
          currentState.value.errorMessage =
            "Chatliste konnte nicht geladen werden.";
        }
      }
    }
  }

  async function refreshSelectedChat() {
    const state = currentState.value;
    const chatId = state.chatId;

    if (
      chatId === undefined
      || state.activeTurn
    ) {
      return;
    }

    let detail;

    try {
      detail = await chatManagement.getChat(chatId);
    } catch (error) {
      console.error("[chat] failed to refresh selected chat", error);
      return;
    }

    if (
      currentState.value !== state
      || state.chatId !== chatId
      || state.activeTurn
    ) {
      return;
    }

    state.messages.splice(
      0,
      state.messages.length,
      ...detail.messages.map(toChatMessage),
    );
    applyCompressionStatus(state, detail.compression_error_code);
  }

  async function selectChat(chatId: number) {
    if (currentState.value.chatId === chatId) {
      return;
    }

    const runningState = chatStates.get(chatId);
    if (runningState?.activeTurn) {
      currentState.value.input = "";
      runningState.input = "";
      currentState.value = runningState;
      return;
    }

    let detail;

    try {
      detail = await chatManagement.getChat(chatId);

    } catch (error) {
      console.error("[chat] failed to load chat", error);
      currentState.value.errorMessage =
        "Chat konnte nicht geladen werden.";
      return;
    }

    currentState.value.input = "";

    const state = createChatState(
      detail.id,
      detail.messages.map(toChatMessage),
    );
    applyCompressionStatus(state, detail.compression_error_code);

    chatStates.set(detail.id, state);
    currentState.value = state;
  }

  function newChat() {
    if (
      currentState.value.chatId === undefined
      && currentState.value.messages.length === 0
      && currentState.value.input.length === 0
      && currentState.value.errorMessage === undefined
    ) {
      return;
    }

    currentState.value.input = "";
    currentState.value = createChatState();
  }

  function updateChatSummary(summary: ChatSummary) {
    const index = chatSummaries.value.findIndex(
      (chat) => chat.id === summary.id,
    );

    if (index !== -1) {
      chatSummaries.value[index] = summary;
    }
  }

  async function renameChat(
    chatId: number,
    title: string,
  ): Promise<boolean> {
    try {
      const summary = await chatManagement.renameChat(
        chatId,
        title,
      );
      updateChatSummary(summary);
      return true;
    } catch (error) {
      console.error("[chat] failed to rename chat", error);
      currentState.value.errorMessage =
        "Chat konnte nicht umbenannt werden.";
      return false;
    }
  }

  async function setChatPinned(
    chatId: number,
    pinned: boolean,
  ): Promise<boolean> {
    try {
      const summary = await chatManagement.setChatPinned(
        chatId,
        pinned,
      );
      updateChatSummary(summary);
      return true;
    } catch (error) {
      console.error("[chat] failed to update pin state", error);
      currentState.value.errorMessage =
        "Pin-Status konnte nicht geändert werden.";
      return false;
    }
  }

  async function deleteChat(chatId: number): Promise<boolean> {
    try {
      await chatManagement.deleteChat(chatId);
    } catch (error) {
      console.error("[chat] failed to delete chat", error);
      currentState.value.errorMessage =
        "Chat konnte nicht gelöscht werden.";
      return false;
    }

    chatSummaries.value = chatSummaries.value.filter(
      (chat) => chat.id !== chatId,
    );
    chatStates.delete(chatId);
    runningChatIds.delete(chatId);

    if (currentState.value.chatId === chatId) {
      currentState.value = createChatState();
    }

    return true;
  }

  async function send() {

    const state = currentState.value;

    if (
      state.activeTurn
      || isChatCompressionFailed.value
      || state.input.length === 0
    ) {
      return;
    }

    const prompt = state.input;
    const startIndex = state.messages.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt,
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "text",
      done: false,
    };

    state.activeTurn = markRaw(turn);
    state.backendPending = true;
    state.errorMessage = undefined;
    state.input = "";

    state.messages.push(
      {
        role: "user",
        content: prompt,
      },
      {
        role: "assistant",
        content: "",
      },
    );

    if (state.chatId !== undefined) {
      runningChatIds.add(state.chatId);
    }

    const request: ChatStreamRequest = state.chatId === undefined
      ? { message: prompt }
      : {
          chatId: state.chatId,
          message: prompt,
        };

    try {
      await streamMessage(
        request,
        {
          onChat(chatId) {
            if (
              state.chatId !== undefined
              && state.chatId !== chatId
            ) {
              throw new Error("Chat stream returned a different chat ID");
            }

            state.chatId = chatId;
            chatStates.set(chatId, state);
            runningChatIds.add(chatId);
          },
          onChunk(text) {
            if (state.activeTurn !== turn) {
              return;
            }

            if (text.length > 0) {
              state.backendPending = false;
            }
            state.messages[turn.assistantIndex].content += text;
          },
          onDone() {
            if (state.activeTurn === turn) {
              turn.done = true;
            }
          },
        },
        controller.signal,
      );
    } catch (error) {
      if (state.activeTurn !== turn) {
        return;
      }

      rollbackTurn(state, turn);

      if (!controller.signal.aborted) {
        console.error("[chat] response generation failed", error);
        const code = error instanceof Error ? error.message : "";
        state.errorMessage = code.includes("AbortException")
          ? "Der Vorgang wurde abgebrochen."
          : code.includes("AuthorizationTimeout")
            ? "Die Freigabe ist abgelaufen."
            : code.includes("PermissionDenied")
              ? "Diese Aktion ist nicht erlaubt."
              : "Antwort konnte nicht erzeugt werden.";
      }
    } finally {
      state.backendPending = false;
      if (state.activeTurn === turn) {
        state.activeTurn = undefined;
      }

      if (state.chatId !== undefined) {
        runningChatIds.delete(state.chatId);
      }

      await refreshSelectedChat();
      await refreshChats();
    }
  }

  async function sendAudio() {
    const state = currentState.value;

    if (state.activeTurn || isChatCompressionFailed.value) {
      return;
    }

    const context = conversationContext(state);
    const startIndex = state.messages.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt: "",
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "audio",
      done: false,
    };

    state.activeTurn = markRaw(turn);
    state.backendPending = true;
    state.errorMessage = undefined;

    state.messages.push(
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "",
      },
    );

    if (state.chatId !== undefined) {
      runningChatIds.add(state.chatId);
    }

    let transcript = "";
    let transcriptFailed = false;

    try {
      await streamAudio(
        context,
        {
          onChat(chatId) {
            acceptAudioChatId(state, chatId);
          },
          onChunk(text) {
            if (state.activeTurn === turn) {
              if (text.length > 0) {
                state.backendPending = false;
              }
              state.messages[turn.assistantIndex].content += text;
            }
          },
          onTranscriptChunk(text) {
            if (state.activeTurn !== turn || transcriptFailed) {
              return;
            }

            transcript += text;
            state.messages[startIndex].content = transcript;
          },
          onTranscriptError() {
            if (state.activeTurn !== turn) {
              return;
            }

            transcriptFailed = true;
            transcript = "";
            state.messages[startIndex].content = "🎤 Sprachnachricht";
          },
          onDone() {
            if (state.activeTurn === turn) {
              turn.done = true;
            }
          },
        },
        controller.signal,
        state.chatId,
      );
    } catch (error) {
      if (state.activeTurn !== turn) {
        return;
      }

      state.messages.splice(turn.assistantIndex, 1);

      if (!controller.signal.aborted) {
        console.error("[audio] response generation failed", error);
        state.errorMessage =
          "Sprachantwort konnte nicht erzeugt werden.";
      }
    } finally {
      state.backendPending = false;
      if (state.activeTurn === turn) {
        state.activeTurn = undefined;
      }

      if (state.chatId !== undefined) {
        runningChatIds.delete(state.chatId);
      }
    }
  }

  async function sendDialogAudio(): Promise<DialogTurnResult | undefined> {
    const state = currentState.value;

    if (state.activeTurn || isChatCompressionFailed.value) {
      return undefined;
    }

    const context = conversationContext(state);
    const startIndex = state.messages.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt: "",
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
      kind: "dialog",
      done: false,
      responding: false,
    };

    state.activeTurn = markRaw(turn);
    // A dialog starts by listening.  Backend work begins only once the
    // recorder reports that the spoken turn has completed.
    state.backendPending = false;
    state.dialogProcessing = false;
    state.errorMessage = undefined;

    let responseStarted = false;
    let messagesCreated = false;
    let transcript = "";
    let transcriptFailed = false;

    function ensureMessages() {
      if (messagesCreated) {
        return;
      }

      messagesCreated = true;
      state.messages.push(
        {
          role: "user",
          content: "🎤 Sprachnachricht",
          kind: "audio",
        },
        {
          role: "assistant",
          content: "",
        },
      );
    }

    try {
      await streamDialog(
        context,
        {
          onChat(chatId) {
            acceptAudioChatId(state, chatId);
          },
          onProcessing() {
            if (state.activeTurn === turn) {
              state.dialogProcessing = true;
              state.backendPending = true;
            }
          },
          onChunk(text) {
            if (state.activeTurn !== turn) {
              return;
            }

            ensureMessages();

            if (!responseStarted) {
              responseStarted = true;
              turn.responding = true;
            }

            if (text.length > 0) {
              state.backendPending = false;
            }

            state.messages[turn.assistantIndex].content += text;
          },
          onTranscriptChunk(text) {
            if (state.activeTurn !== turn || transcriptFailed) {
              return;
            }

            ensureMessages();
            transcript += text;
            state.messages[startIndex].content = transcript;
          },
          onTranscriptError() {
            if (state.activeTurn !== turn) {
              return;
            }

            transcriptFailed = true;
            transcript = "";

            if (messagesCreated) {
              state.messages[startIndex].content = "🎤 Sprachnachricht";
            }
          },
          onDone() {
            if (state.activeTurn === turn) {
              turn.done = true;
            }
          },
        },
        controller.signal,
        state.chatId,
      );

      if (!responseStarted) {
        return undefined;
      }

      return {
        assistantIndex: turn.assistantIndex,
      };
    } catch (error) {
      if (state.activeTurn !== turn) {
        return undefined;
      }

      if (messagesCreated) {
        state.messages.splice(turn.assistantIndex, 1);
      }

      if (!controller.signal.aborted) {
        console.error("[audio-dialog] dialog turn failed", error);
        state.errorMessage =
          "Dialogantwort konnte nicht erzeugt werden.";
      }

      return undefined;
    } finally {
      state.backendPending = false;
      state.dialogProcessing = false;
      if (state.activeTurn === turn) {
        turn.responding = false;
        state.activeTurn = undefined;
      }
    }
  }

  function abortDialogTurn() {
    const state = currentState.value;
    const turn = state.activeTurn;

    if (
      !turn
      || turn.kind !== "dialog"
      || turn.responding
    ) {
      return;
    }

    turn.controller.abort();
    state.backendPending = false;
    state.dialogProcessing = false;
    state.activeTurn = undefined;
  }

  function stop() {
    const state = currentState.value;
    const turn = state.activeTurn;

    if (!turn) {
      return;
    }

    turn.controller.abort();
    state.backendPending = false;
    state.dialogProcessing = false;

    if (turn.kind === "audio" || turn.kind === "dialog") {
      const userMessage = state.messages[turn.startIndex];

      if (userMessage?.role === "user") {
        userMessage.content = "🎤 Sprachnachricht";
        state.messages.splice(turn.assistantIndex, 1);
      }
    } else {
      rollbackTurn(state, turn);
    }

    state.activeTurn = undefined;

    if (state.chatId !== undefined) {
      runningChatIds.delete(state.chatId);
    }
  }

  function isChatRunning(chatId: number) {
    return runningChatIds.has(chatId);
  }

  return {
    messages,
    input,
    isGenerating,
    isDialogResponding,
    isDialogProcessing,
    backendPending,
    errorMessage,
    chatSummaries,
    selectedChatId,
    isChatCompressionFailed,
    refreshChats,
    refreshSelectedChat,
    selectChat,
    newChat,
    renameChat,
    setChatPinned,
    deleteChat,
    isChatRunning,
    send,

    sendAudio,
    sendDialogAudio,
    abortDialogTurn,
    stop,
  };
}
