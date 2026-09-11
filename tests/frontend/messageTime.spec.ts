import { describe, expect, it } from "vitest";

import {
  formatMessageTime,
} from "../../frontend/src/services/messageTime";

describe("formatMessageTime", () => {
  it("shows only local time for messages from today", () => {
    const message = {
      role: "user" as const,
      content: "Hallo",
      created_at: "2026-09-11T08:05:00",
    };

    expect(
      formatMessageTime(
        message,
        new Date("2026-09-11T20:00:00"),
      ),
    ).toBe("08:05");
  });

  it("shows local date and time for older messages", () => {
    const message = {
      role: "assistant" as const,
      content: "Hallo",
      created_at: "2026-09-10T08:05:00",
    };

    expect(
      formatMessageTime(
        message,
        new Date("2026-09-11T20:00:00"),
      ),
    ).toBe("2026-09-10 08:05");
  });

  it("keeps the first local time assigned to a transient message", () => {
    const message = {
      role: "user" as const,
      content: "Hallo",
    };

    expect(
      formatMessageTime(
        message,
        new Date("2026-09-11T20:01:00"),
      ),
    ).toBe("20:01");

    expect(
      formatMessageTime(
        message,
        new Date("2026-09-11T20:05:00"),
      ),
    ).toBe("20:01");
  });
});