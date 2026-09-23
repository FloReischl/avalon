import { describe, expect, it } from "vitest";

import {
  boundCallChatToSelect,
} from "../../frontend/src/services/audioCallBinding";

describe("boundCallChatToSelect", () => {
  it("selects a newly bound audio-call chat", () => {
    expect(
      boundCallChatToSelect(
        {
          active: true,
          chat_id: 42,
          turn_active: false,
          pending_speech: null,
        },
        undefined,
      ),
    ).toBe(42);
  });

  it("does not reload the selected, inactive, or unbound chat", () => {
    expect(
      boundCallChatToSelect(
        {
          active: true,
          chat_id: 42,
          turn_active: false,
          pending_speech: null,
        },
        42,
      ),
    ).toBeUndefined();
    expect(
      boundCallChatToSelect(
        {
          active: false,
          chat_id: 42,
          turn_active: false,
          pending_speech: null,
        },
        undefined,
      ),
    ).toBeUndefined();
    expect(
      boundCallChatToSelect(
        {
          active: true,
          chat_id: null,
          turn_active: false,
          pending_speech: null,
        },
        undefined,
      ),
    ).toBeUndefined();
  });
});