import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { openExternalLink } from "../../frontend/src/services/externalLinks";

describe("openExternalLink", () => {
  const invokeMock = vi.fn();

  beforeEach(() => {
    invokeMock.mockReset();
  });

  afterEach(() => {
    Reflect.deleteProperty(globalThis, "isTauri");
    Reflect.deleteProperty(window, "__TAURI_INTERNALS__");
  });

  it("uses the Tauri opener inside Tauri", async () => {
    Object.defineProperty(globalThis, "isTauri", {
      configurable: true,
      value: true,
    });

    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {
        invoke: invokeMock.mockResolvedValue(undefined),
      },
    });

    await openExternalLink("https://example.com/path");

    expect(invokeMock).toHaveBeenCalled();
  });

  it("uses a new browser tab outside Tauri", async () => {
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
    Object.defineProperty(globalThis, "isTauri", {
      configurable: true,
      value: true,
    });

    Object.defineProperty(window, "__TAURI_INTERNALS__", {
      configurable: true,
      value: {
        invoke: invokeMock.mockResolvedValue(undefined),
      },
    });

    await expect(
      openExternalLink("javascript:alert('nope')"),
    ).rejects.toThrow("Unsupported external link protocol");

    expect(invokeMock).not.toHaveBeenCalled();
  });
});
