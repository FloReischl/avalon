import { beforeEach, describe, expect, it, vi } from "vitest";

const getChatMock = vi.fn();
const saveMock = vi.fn();
const writeTextFileMock = vi.fn();

const dependencies = {
  getChat: getChatMock,
  save: saveMock,
  writeTextFile: writeTextFileMock,
};

import {
  buildChatMarkdown,
  exportChatToMarkdown,
  getChatMarkdown,
  sanitizeChatExportFilename,
} from "../../frontend/src/services/chatExport";

describe("chat export", () => {
  beforeEach(() => {
    getChatMock.mockReset();
    saveMock.mockReset();
    writeTextFileMock.mockReset();
    writeTextFileMock.mockResolvedValue(undefined);
  });

  it("builds Markdown from stored messages without transforming their content", () => {
    const markdown = buildChatMarkdown(
      [
        {
          id: 1,
          role: "user",
          content: "**Frage**\n\n- eins\n- zwei",
          created_at: "2026-09-08T10:00:00",
        },
        {
          id: 2,
          role: "assistant",
          content: "## Antwort\n\n`code`",
          created_at: "2026-09-08T10:00:01",
        },
        {
          id: 3,
          role: "user",
          content: "Weiter",
          created_at: "2026-09-08T10:00:02",
        },
      ],
      "Frieda",
    );

    expect(markdown).toBe(
      "# User\n\n"
      + "**Frage**\n\n- eins\n- zwei\n"
      + "---\n"
      + "# Frieda\n\n"
      + "## Antwort\n\n`code`\n"
      + "---\n"
      + "# User\n\n"
      + "Weiter\n",
    );
    expect(markdown.endsWith("---\n")).toBe(false);
  });

  it("loads persisted chat Markdown using the shared Markdown builder", async () => {
    getChatMock.mockResolvedValue({
      id: 42,
      title: "Chat",
      pinned: false,
      created_at: "2026-09-08T10:00:00",
      messages: [
        {
          id: 1,
          role: "user",
          content: "Frage",
          created_at: "2026-09-08T10:00:01",
        },
        {
          id: 2,
          role: "assistant",
          content: "Antwort",
          created_at: "2026-09-08T10:00:02",
        },
      ],
    });

    await expect(
      getChatMarkdown(
        42,
        "Frieda",
        getChatMock,
      ),
    ).resolves.toBe(
      "# User\n\nFrage\n---\n# Frieda\n\nAntwort\n",
    );

    expect(getChatMock).toHaveBeenCalledWith(42);
  });

  it("sanitizes problematic filename characters and falls back to chat", () => {
    expect(
      sanitizeChatExportFilename('Plan: "A/B" <Test>?*'),
    ).toBe("Plan_ _A_B_ _Test___.md");

    expect(
      sanitizeChatExportFilename("...   "),
    ).toBe("chat.md");
  });

  it("loads the persisted chat before opening the save dialog and writes it", async () => {
    getChatMock.mockResolvedValue({
      id: 42,
      title: "Persistenter Chat",
      pinned: false,
      created_at: "2026-09-08T10:00:00",
      messages: [
        {
          id: 1,
          role: "user",
          content: "Frage",
          created_at: "2026-09-08T10:00:01",
        },
        {
          id: 2,
          role: "assistant",
          content: "Antwort",
          created_at: "2026-09-08T10:00:02",
        },
      ],
    });
    saveMock.mockResolvedValue("/tmp/Persistenter Chat.md");

    await exportChatToMarkdown(
      42,
      "Frieda",
      dependencies,
    );

    expect(getChatMock).toHaveBeenCalledWith(42);
    expect(saveMock).toHaveBeenCalledWith({
      defaultPath: "Persistenter Chat.md",
      filters: [
        {
          name: "Markdown",
          extensions: ["md"],
        },
      ],
    });
    expect(writeTextFileMock).toHaveBeenCalledWith(
      "/tmp/Persistenter Chat.md",
      "# User\n\nFrage\n---\n# Frieda\n\nAntwort\n",
    );
  });

  it("does not write a file when the save dialog is cancelled", async () => {
    getChatMock.mockResolvedValue({
      id: 42,
      title: "Chat",
      pinned: false,
      created_at: "2026-09-08T10:00:00",
      messages: [],
    });
    saveMock.mockResolvedValue(null);

    await exportChatToMarkdown(
      42,
      "Frieda",
      dependencies,
    );

    expect(writeTextFileMock).not.toHaveBeenCalled();
  });

  it("propagates persisted chat load failures", async () => {
    getChatMock.mockRejectedValue(new Error("load failed"));

    await expect(
      exportChatToMarkdown(
        42,
        "Frieda",
        dependencies,
      ),
    ).rejects.toThrow("load failed");

    expect(saveMock).not.toHaveBeenCalled();
    expect(writeTextFileMock).not.toHaveBeenCalled();
  });

  it("propagates file write failures", async () => {
    getChatMock.mockResolvedValue({
      id: 42,
      title: "Chat",
      pinned: false,
      created_at: "2026-09-08T10:00:00",
      messages: [],
    });
    saveMock.mockResolvedValue("/tmp/Chat.md");
    writeTextFileMock.mockRejectedValue(new Error("write failed"));

    await expect(
      exportChatToMarkdown(
        42,
        "Frieda",
        dependencies,
      ),
    ).rejects.toThrow("write failed");
  });
});