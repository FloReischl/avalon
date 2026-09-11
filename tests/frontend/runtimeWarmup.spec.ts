import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const { warmUpRuntimeMock } = vi.hoisted(() => ({
  warmUpRuntimeMock: vi.fn(),
}));

vi.mock("../../frontend/src/services/backend", () => ({
  warmUpRuntime: warmUpRuntimeMock,
}));

import {
  requestRuntimeWarmUp,
} from "../../frontend/src/services/runtimeWarmup";

describe("runtimeWarmup", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-11T18:00:00Z"));
    warmUpRuntimeMock.mockReset();
    warmUpRuntimeMock.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("sends at most one warm-up request per minute", () => {
    requestRuntimeWarmUp();
    requestRuntimeWarmUp();

    expect(warmUpRuntimeMock).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(59_999);
    requestRuntimeWarmUp();

    expect(warmUpRuntimeMock).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(1);
    requestRuntimeWarmUp();

    expect(warmUpRuntimeMock).toHaveBeenCalledTimes(2);
  });
});