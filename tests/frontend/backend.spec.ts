import { afterEach, describe, expect, it, vi } from "vitest";

import {
  abortAudioRecording,
  startAudioRecording,
  streamAudioResponse,
  streamChatMessage,
} from "../../frontend/src/services/backend";

function createStreamingResponse(parts: string[]): Response {
  const encoder = new TextEncoder();

  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const part of parts) {
        controller.enqueue(encoder.encode(part));
      }
      controller.close();
    },
  });

  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
    },
  });
}

describe("streamChatMessage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("forwards chunk events in order until done", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      createStreamingResponse([
        'event: chunk\ndata: {"text": "Hallo "}\n',
        '\nevent: chunk\ndata: {"text": "Flo"}\n\n',
        "event: done\ndata: {}\n\n",
      ]),
    );

    const chunks: string[] = [];

    await streamChatMessage(
      [{ role: "user", content: "Hallo" }],
      {
        onChunk: (text) => chunks.push(text),
      },
      new AbortController().signal,
    );

    expect(chunks).toEqual(["Hallo ", "Flo"]);
    expect(fetch).toHaveBeenCalledWith(
      "http://127.0.0.1:8095/api/v1/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          messages: [{ role: "user", content: "Hallo" }],
        }),
      }),
    );
  });

  it("rejects an error event", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      createStreamingResponse([
        "event: error\ndata: {}\n\n",
      ]),
    );

    await expect(
      streamChatMessage(
        [{ role: "user", content: "Hallo" }],
        {
          onChunk: () => {},
        },
        new AbortController().signal,
      ),
    ).rejects.toThrow("Chat generation failed");
  });

  it("rejects a stream that ends without done", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      createStreamingResponse([
        'event: chunk\ndata: {"text": "Hallo"}\n\n',
      ]),
    );

    await expect(
      streamChatMessage(
        [{ role: "user", content: "Hallo" }],
        {
          onChunk: () => {},
        },
        new AbortController().signal,
      ),
    ).rejects.toThrow("Chat stream ended without done event");
  });

  it("controls capture and streams audio responses with context", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(createStreamingResponse([
        'event: chunk\ndata: {"text": "Hallo"}\n\n',
        "event: done\ndata: {}\n\n",
      ]))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await startAudioRecording();
    const chunks: string[] = [];
    await streamAudioResponse(
      [{ role: "user", content: "Kontext" }],
      { onChunk: (text) => chunks.push(text) },
      new AbortController().signal,
    );
    await abortAudioRecording();

    expect(chunks).toEqual(["Hallo"]);
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      "http://127.0.0.1:8095/api/v1/audio/recording/stop",
      expect.objectContaining({
        body: JSON.stringify({
          messages: [{ role: "user", content: "Kontext" }],
        }),
      }),
    );
  });
});
