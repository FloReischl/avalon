import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

const {
  setAgentBearerTokenMock,
} = vi.hoisted(() => ({
  setAgentBearerTokenMock: vi.fn(),
}));

vi.mock("../../frontend/src/services/backend", () => ({
  BACKEND_BASE_URL: "http://127.0.0.1:8095",
  setAgentBearerToken: setAgentBearerTokenMock,
}));

const uiConfigResponse = {
  name: "Frieda",
  agentBearerToken: "test-token",
  avatar: {
    greetingAudioUrl:
      "http://127.0.0.1:8095/api/v1/assets/avatar/greeting",
    standard: {
      key: "standard" as const,
      url: "http://127.0.0.1:8095/api/v1/assets/avatar/images/standard",
    },
    animations: [],
  },
};

function successfulResponse(): Response {
  return new Response(
    JSON.stringify(uiConfigResponse),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
      },
    },
  );
}

function errorResponse(status: number): Response {
  return new Response(null, { status });
}

async function loadFreshUiConfigModule() {
  vi.resetModules();
  return import("../../frontend/src/uiConfig");
}

describe("uiConfig", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setAgentBearerTokenMock.mockReset();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("loads UI config without retry on the first successful request", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(successfulResponse());

    const { loadUiConfig } = await loadFreshUiConfigModule();

    await expect(loadUiConfig()).resolves.toEqual(uiConfigResponse);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8095/api/v1/ui/config",
    );
    expect(setAgentBearerTokenMock).toHaveBeenCalledOnce();
    expect(setAgentBearerTokenMock).toHaveBeenCalledWith(
      "test-token",
    );
  });

  it("retries HTTP 5xx after 500 ms and succeeds", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(errorResponse(503))
      .mockResolvedValueOnce(successfulResponse());

    const { loadUiConfig } = await loadFreshUiConfigModule();

    const result = loadUiConfig();
    await vi.advanceTimersByTimeAsync(499);

    expect(fetchMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1);

    await expect(result).resolves.toEqual(uiConfigResponse);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("retries a transport error and succeeds", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockRejectedValueOnce(new TypeError("Load failed"))
      .mockResolvedValueOnce(successfulResponse());

    const { loadUiConfig } = await loadFreshUiConfigModule();

    const result = loadUiConfig();
    await vi.advanceTimersByTimeAsync(500);

    await expect(result).resolves.toEqual(uiConfigResponse);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not retry HTTP 4xx", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(errorResponse(404));

    const { loadUiConfig } = await loadFreshUiConfigModule();

    await expect(loadUiConfig()).rejects.toThrow(
      "UI config request failed with HTTP 404",
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("stops after ten retries for persistent HTTP 5xx", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(errorResponse(503));

    const { loadUiConfig } = await loadFreshUiConfigModule();

    const result = loadUiConfig();
    const rejection = expect(result).rejects.toThrow(
      "UI config request failed with HTTP 503",
    );

    await vi.advanceTimersByTimeAsync(5000);

    await rejection;
    expect(fetchMock).toHaveBeenCalledTimes(11);
  });

  it("shares one request and retry sequence between concurrent callers", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(errorResponse(503))
      .mockResolvedValueOnce(successfulResponse());

    const { loadUiConfig } = await loadFreshUiConfigModule();

    const first = loadUiConfig();
    const second = loadUiConfig();

    expect(fetchMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(500);

    await expect(first).resolves.toEqual(uiConfigResponse);
    await expect(second).resolves.toEqual(uiConfigResponse);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
