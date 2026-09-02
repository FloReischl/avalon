import { afterEach, describe, expect, it, vi } from "vitest";

import { streamChatMessage } from "../../frontend/src/services/backend";

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
      "Hallo",
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
        body: JSON.stringify({ message: "Hallo" }),
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
        "Hallo",
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
        "Hallo",
        {
          onChunk: () => {},
        },
        new AbortController().signal,
      ),
    ).rejects.toThrow("Chat stream ended without done event");
  });
});
