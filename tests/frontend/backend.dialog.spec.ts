import { afterEach, describe, expect, it, vi } from "vitest";

import { streamDialogResponse } from "../../frontend/src/services/backend";


afterEach(() => {
  vi.restoreAllMocks();
});


describe("streamDialogResponse", () => {
  it("posts chat context to the dialog turn endpoint and consumes SSE", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        [
          'event: chunk\ndata: {"text":"Hallo"}',
          "",
          'event: chunk\ndata: {"text":" Flo"}',
          "",
          "event: done\ndata: {}",
          "",
        ].join("\n") + "\n",
        {
          status: 200,
          headers: {
            "Content-Type": "text/event-stream",
          },
        },
      ),
    );

    const controller = new AbortController();
    const chunks: string[] = [];
    const onDone = vi.fn();

    await streamDialogResponse(
      [
        {
          role: "user",
          content: "Vorherige Nachricht",
        },
        {
          role: "assistant",
          content: "Vorherige Antwort",
        },
      ],
      {
        onChunk(text) {
          chunks.push(text);
        },
        onDone,
      },
      controller.signal,
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, options] = fetchMock.mock.calls[0];

    expect(url).toBe(
      "http://127.0.0.1:8095/api/v1/audio/dialog/turn",
    );
    expect(options).toMatchObject({
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });
    expect(JSON.parse(String(options?.body))).toEqual({
      messages: [
        {
          role: "user",
          content: "Vorherige Nachricht",
        },
        {
          role: "assistant",
          content: "Vorherige Antwort",
        },
      ],
    });

    expect(chunks).toEqual(["Hallo", " Flo"]);
    expect(onDone).toHaveBeenCalledTimes(1);
  });


  it("passes abort through to fetch", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (_url, options) =>
        await new Promise<Response>((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const controller = new AbortController();

    const request = streamDialogResponse(
      [],
      {
        onChunk() {},
      },
      controller.signal,
    );

    controller.abort();

    await expect(request).rejects.toMatchObject({
      name: "AbortError",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});