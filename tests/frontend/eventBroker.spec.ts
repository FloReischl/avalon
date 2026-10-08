import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  BROKER_EVENT_TYPES,
  EventBroker,
} from "../../frontend/src/services/eventBroker";

type Listener = (event: Event | MessageEvent) => void;

const eventSources: EventSourceMock[] = [];

class EventSourceMock {
  readonly listeners = new Map<string, Listener[]>();
  readonly close = vi.fn();

  constructor(readonly url: string) {
    eventSources.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    const listeners = this.listeners.get(type) ?? [];
    listeners.push(listener);
    this.listeners.set(type, listeners);
  }

  dispatch(type: string, data?: unknown): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(data === undefined ? new Event(type) : new MessageEvent(type, { data }));
    }
  }
}

describe("eventBroker", () => {
  const emitMock = vi.fn();
  let eventBroker: EventBroker;

  beforeEach(() => {
    eventSources.splice(0);
    emitMock.mockReset();
    emitMock.mockResolvedValue(undefined);
    eventBroker = new EventBroker(emitMock);
    vi.stubGlobal("EventSource", EventSourceMock);
  });

  afterEach(() => {
    eventBroker.stop();
    vi.unstubAllGlobals();
  });

  it("starts only one EventSource and stops it", () => {

    eventBroker.start();
    eventBroker.start();

    expect(eventSources).toHaveLength(1);
    expect(eventSources[0].url).toBe("http://127.0.0.1:8095/api/v1/events");

    eventBroker.stop();
    expect(eventSources[0].close).toHaveBeenCalledTimes(1);
  });

  it("forwards all broker event payloads unchanged", async () => {
    eventBroker.start();
    const source = eventSources[0];

    for (const eventType of BROKER_EVENT_TYPES) source.dispatch(eventType, `payload:${eventType}`);

    await Promise.resolve();
    expect(emitMock).toHaveBeenCalledWith("authorization_requests_changed", "payload:authorization_requests_changed");
    expect(emitMock).toHaveBeenCalledWith("workflow_confirmations_changed", "payload:workflow_confirmations_changed");
    expect(emitMock).toHaveBeenCalledWith("workflow_execution", "payload:workflow_execution");
  });

  it("invalidates all domains on initial open and reconnect", async () => {
    eventBroker.start();
    const source = eventSources[0];

    source.dispatch("open");
    source.dispatch("open");

    await Promise.resolve();
    expect(emitMock.mock.calls).toEqual([
      ...BROKER_EVENT_TYPES.map((eventType) => [eventType, undefined]),
      ...BROKER_EVENT_TYPES.map((eventType) => [eventType, undefined]),
    ]);
  });

  it("keeps running when Tauri event forwarding fails", async () => {
    const error = new Error("Tauri unavailable");
    emitMock.mockRejectedValueOnce(error);
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    eventBroker.start();

    eventSources[0].dispatch("authorization_requests_changed", "payload");
    await Promise.resolve();

    expect(errorSpy).toHaveBeenCalledWith("[event-broker] failed to forward event", "authorization_requests_changed", error);
    eventSources[0].dispatch("workflow_execution", "still-running");
    await Promise.resolve();
    expect(emitMock).toHaveBeenCalledWith("workflow_execution", "still-running");
    errorSpy.mockRestore();
  });

  it("does not forward callbacks from a stopped EventSource", async () => {
    eventBroker.start();
    const source = eventSources[0];
    eventBroker.stop();
    source.dispatch("open");
    source.dispatch("workflow_execution", "stale");

    await Promise.resolve();
    expect(emitMock).not.toHaveBeenCalled();
  });
});
