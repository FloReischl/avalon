import { ref } from "vue";

import { streamChatMessage } from "../services/backend";
import type { ChatMessage } from "../types/chat";

export type ChatStreamer = (
  message: string,
  handlers: {
    onChunk: (text: string) => void;
  },
  signal: AbortSignal,
) => Promise<void>;

interface ActiveTurn {
  prompt: string;
  startIndex: number;
  assistantIndex: number;
  controller: AbortController;
}

export function useTransientChat(
  streamMessage: ChatStreamer = streamChatMessage,
) {
  const messages = ref<ChatMessage[]>([]);
  const input = ref("");
  const isGenerating = ref(false);
  const errorMessage = ref<string | undefined>();

  let activeTurn: ActiveTurn | undefined;

  function rollbackTurn(turn: ActiveTurn) {
    messages.value.splice(turn.startIndex);
    input.value = turn.prompt;
  }

  async function send() {
    if (isGenerating.value || input.value.length === 0) {
      return;
    }

    const prompt = input.value;
    const startIndex = messages.value.length;
    const controller = new AbortController();

    const turn: ActiveTurn = {
      prompt,
      startIndex,
      assistantIndex: startIndex + 1,
      controller,
    };

    activeTurn = turn;
    errorMessage.value = undefined;
    input.value = "";
    isGenerating.value = true;

    messages.value.push(
      {
        role: "user",
        content: prompt,
      },
      {
        role: "assistant",
        content: "",
      },
    );

    try {
      await streamMessage(
        prompt,
        {
          onChunk(text) {
            if (activeTurn !== turn) {
              return;
            }

            messages.value[turn.assistantIndex].content += text;
          },
        },
        controller.signal,
      );
    } catch {
      if (activeTurn !== turn) {
        return;
      }

      rollbackTurn(turn);

      if (!controller.signal.aborted) {
        errorMessage.value = "Antwort konnte nicht erzeugt werden.";
      }
    } finally {
      if (activeTurn === turn) {
        activeTurn = undefined;
        isGenerating.value = false;
      }
    }
  }

  function stop() {
    const turn = activeTurn;
    if (!turn) {
      return;
    }

    turn.controller.abort();
    rollbackTurn(turn);
    activeTurn = undefined;
    isGenerating.value = false;
  }

  return {
    messages,
    input,
    isGenerating,
    errorMessage,
    send,
    stop,
  };
}
