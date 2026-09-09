import { nextTick } from "vue";
import { describe, expect, it, vi } from "vitest";

import {
  useTransientChat,
  type AudioStreamer,
  type ChatManagementClient,
  type ChatStreamer,
} from "../../frontend/src/composables/useTransientChat";


function deferred<T>() {
  let resolve!: (value: T) => void;

  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });

  return {
    promise,
    resolve,
  };
}


const unusedChatStreamer: ChatStreamer = async () => {
  throw new Error("Text chat must not be used by dialog tests");
};


const unusedAudioStreamer: AudioStreamer = async () => {
  throw new Error("PTT audio must not be used by dialog tests");
};


const chatManagement: ChatManagementClient = {
  getChats: async () => [],
  getChat: async () => {
    throw new Error("getChat must not be used");
  },
  renameChat: async () => {
    throw new Error("renameChat must not be used");
  },
  setChatPinned: async () => {
    throw new Error("setChatPinned must not be used");
  },
  deleteChat: async () => {},
};


describe("useTransientChat dialog turns", () => {
  it("waits without reporting generation until the first response chunk", async () => {
    const started = deferred<void>();
    const releaseResponse = deferred<void>();

    const streamDialog: AudioStreamer = async (
      _messages,
      handlers,
    ) => {
      started.resolve(undefined);

      await releaseResponse.promise;

      handlers.onChunk("Hallo");
      handlers.onDone?.();
    };

    const chat = useTransientChat(
      unusedChatStreamer,
      unusedAudioStreamer,
      chatManagement,
      streamDialog,
    );

    const turn = chat.sendDialogAudio();

    await started.promise;
    await nextTick();

    expect(chat.isGenerating.value).toBe(false);
    expect(chat.isDialogResponding.value).toBe(false);
    expect(chat.messages.value).toEqual([]);

    releaseResponse.resolve(undefined);

    const result = await turn;
    await nextTick();

    expect(result).toEqual({
      assistantIndex: 1,
    });
    expect(chat.messages.value).toEqual([
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "Hallo",
      },
    ]);
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.isDialogResponding.value).toBe(false);
  });


  it("marks a dialog turn as responding when the first chunk arrives", async () => {
    const chunkSent = deferred<void>();
    const finish = deferred<void>();

    const streamDialog: AudioStreamer = async (
      _messages,
      handlers,
    ) => {
      handlers.onChunk("Hallo");
      chunkSent.resolve(undefined);

      await finish.promise;

      handlers.onChunk(" Flo");
      handlers.onDone?.();
    };

    const chat = useTransientChat(
      unusedChatStreamer,
      unusedAudioStreamer,
      chatManagement,
      streamDialog,
    );

    const turn = chat.sendDialogAudio();

    await chunkSent.promise;
    await nextTick();

    expect(chat.isGenerating.value).toBe(true);
    expect(chat.isDialogResponding.value).toBe(true);
    expect(chat.messages.value).toEqual([
      {
        role: "user",
        content: "🎤 Sprachnachricht",
        kind: "audio",
      },
      {
        role: "assistant",
        content: "Hallo",
      },
    ]);

    finish.resolve(undefined);
    await turn;

    expect(chat.messages.value[1].content).toBe("Hallo Flo");
  });


  it("aborts a listening turn without creating chat messages", async () => {
    const started = deferred<void>();
    let receivedSignal: AbortSignal | undefined;

    const streamDialog: AudioStreamer = async (
      _messages,
      _handlers,
      signal,
    ) => {
      receivedSignal = signal;
      started.resolve(undefined);

      await new Promise<void>((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    };

    const chat = useTransientChat(
      unusedChatStreamer,
      unusedAudioStreamer,
      chatManagement,
      streamDialog,
    );

    const turn = chat.sendDialogAudio();

    await started.promise;

    chat.abortDialogTurn();
    await turn;

    expect(receivedSignal?.aborted).toBe(true);
    expect(chat.messages.value).toEqual([]);
    expect(chat.isGenerating.value).toBe(false);
    expect(chat.isDialogResponding.value).toBe(false);
    expect(chat.errorMessage.value).toBeUndefined();
  });


  it("does not abort the LLM response once a dialog turn is responding", async () => {
    const responding = deferred<void>();
    const finish = deferred<void>();
    let receivedSignal: AbortSignal | undefined;

    const streamDialog: AudioStreamer = async (
      _messages,
      handlers,
      signal,
    ) => {
      receivedSignal = signal;

      handlers.onChunk("Antwort");
      responding.resolve(undefined);

      await finish.promise;

      handlers.onDone?.();
    };

    const chat = useTransientChat(
      unusedChatStreamer,
      unusedAudioStreamer,
      chatManagement,
      streamDialog,
    );

    const turn = chat.sendDialogAudio();

    await responding.promise;

    chat.abortDialogTurn();

    expect(receivedSignal?.aborted).toBe(false);
    expect(chat.isDialogResponding.value).toBe(true);

    finish.resolve(undefined);
    await turn;

    expect(chat.messages.value[1].content).toBe("Antwort");
  });


  it("uses completed audio transcripts in the next dialog context", async () => {
    const contexts: Array<
      Array<{ role: "user" | "assistant"; content: string }>
    > = [];

    const streamDialog: AudioStreamer = async (
      messages,
      handlers,
    ) => {
      contexts.push(messages);

      handlers.onTranscriptChunk?.(
        contexts.length === 1
          ? "Erste Frage"
          : "Zweite Frage",
      );
      handlers.onChunk(
        contexts.length === 1
          ? "Erste Antwort"
          : "Zweite Antwort",
      );
      handlers.onDone?.();
    };

    const chat = useTransientChat(
      unusedChatStreamer,
      unusedAudioStreamer,
      chatManagement,
      streamDialog,
    );

    await chat.sendDialogAudio();
    await chat.sendDialogAudio();

    expect(contexts).toEqual([
      [],
      [
        {
          role: "user",
          content: "Erste Frage",
        },
        {
          role: "assistant",
          content: "Erste Antwort",
        },
      ],
    ]);
  });
});