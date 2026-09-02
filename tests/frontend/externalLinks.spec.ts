import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  isTauriMock,
  openUrlMock,
} = vi.hoisted(() => ({
  isTauriMock: vi.fn(),
  openUrlMock: vi.fn(),
}));

vi.mock("@tauri-apps/api/core", () => ({
  isTauri: isTauriMock,
}));

vi.mock("@tauri-apps/plugin-opener", () => ({
  openUrl: openUrlMock,
}));

import { openExternalLink } from "../../frontend/src/services/externalLinks";

describe("openExternalLink", () => {
  beforeEach(() => {
    isTauriMock.mockReset();
    openUrlMock.mockReset();
  });

  it("uses the Tauri opener inside Tauri", async () => {
    isTauriMock.mockReturnValue(true);
    openUrlMock.mockResolvedValue(undefined);

    await openExternalLink("https://example.com/path");

    expect(openUrlMock).toHaveBeenCalledWith(
      "https://example.com/path",
    );
  });

  it("uses a new browser tab outside Tauri", async () => {
    isTauriMock.mockReturnValue(false);
    const open = vi.spyOn(window, "open").mockImplementation(() => null);

    try {
      await openExternalLink("https://example.com/path");

      expect(open).toHaveBeenCalledWith(
        "https://example.com/path",
        "_blank",
        "noopener,noreferrer",
      );
    } finally {
      open.mockRestore();
    }
  });

  it("rejects unsupported protocols", async () => {
    isTauriMock.mockReturnValue(true);

    await expect(
      openExternalLink("javascript:alert('nope')"),
    ).rejects.toThrow("Unsupported external link protocol");

    expect(openUrlMock).not.toHaveBeenCalled();
  });
});
