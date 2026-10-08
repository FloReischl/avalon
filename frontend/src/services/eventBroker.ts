import { emit } from "@tauri-apps/api/event";

import { BACKEND_BASE_URL } from "./backend";

export const BROKER_EVENT_TYPES = [
  "authorization_requests_changed",
  "workflow_confirmations_changed",
  "workflow_execution",
] as const;

export type BrokerEventType = typeof BROKER_EVENT_TYPES[number];

type EmitEvent = (event: BrokerEventType, payload?: unknown) => Promise<void>;

export class EventBroker {
  private source: EventSource | undefined;

  constructor(private readonly emitEvent: EmitEvent = emit) {}

  start(): void {
    if (this.source || typeof EventSource === "undefined") return;

    const source = new EventSource(`${BACKEND_BASE_URL}/api/v1/events`);
    this.source = source;

    source.addEventListener("open", () => {
      if (this.source !== source) return;
      this.invalidateAll();
    });

    for (const eventType of BROKER_EVENT_TYPES) {
      source.addEventListener(eventType, (event) => {
        if (this.source !== source) return;
        this.forward(eventType, (event as MessageEvent).data);
      });
    }
  }

  stop(): void {
    this.source?.close();
    this.source = undefined;
  }

  private invalidateAll(): void {
    for (const eventType of BROKER_EVENT_TYPES) this.forward(eventType);
  }

  private forward(eventType: BrokerEventType, payload?: unknown): void {
    void this.emitEvent(eventType, payload).catch((error) => {
      console.error("[event-broker] failed to forward event", eventType, error);
    });
  }
}

export const eventBroker = new EventBroker();
