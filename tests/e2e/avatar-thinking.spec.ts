import { expect, test } from "../../frontend/node_modules/@playwright/test";

const standardImage = "data/blueprints/user.avalon/avatars/standard/standard.png";
const thinkingImage = "data/blueprints/user.avalon/avatars/standard/thinking.png";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    let nextCallbackId = 1;
    const callbacks = new Map<number, (event: unknown) => void>();
    const listeners = new Map<string, number[]>();

    Object.assign(window, {
      __emitTauriEvent: (event: string, payload: unknown) => {
        for (const callbackId of listeners.get(event) ?? []) {
          callbacks.get(callbackId)?.({ event, id: callbackId, payload });
        }
      },
      __TAURI_EVENT_PLUGIN_INTERNALS__: { unregisterListener: () => {} },
      __TAURI_INTERNALS__: {
        transformCallback(callback: (event: unknown) => void) {
          const callbackId = nextCallbackId++;
          callbacks.set(callbackId, callback);
          return callbackId;
        },
        unregisterCallback(callbackId: number) {
          callbacks.delete(callbackId);
        },
        async invoke(command: string, args: Record<string, unknown>) {
          if (command === "get_backend_snapshot") {
            return { status: "ready", logs: [] };
          }
          if (command === "plugin:event|listen") {
            const event = args.event as string;
            const handler = args.handler as number;
            listeners.set(event, [...(listeners.get(event) ?? []), handler]);
            return handler;
          }
          return undefined;
        },
      },
    });
  });

  await page.route("**/api/v1/ui/config", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        name: "Frieda",
        agentBearerToken: "test-token",
        avatarZoom: 1,
        avatar: {
          greetingAudioUrl: "/greeting.wav",
          standard: { key: "standard", url: "/avatar/standard.png" },
          animations: [{
            key: "thinking",
            category: "state",
            spriteSetUrl: "/avatar/thinking.png",
            sprites: [
              { x: 77, y: 6, width: 213, height: 590 },
              { x: 411, y: 7, width: 215, height: 587 },
              { x: 789, y: 10, width: 213, height: 587 },
              { x: 1149, y: 9, width: 215, height: 588 },
              { x: 1505, y: 7, width: 223, height: 590 },
            ],
          }],
        },
      }),
    });
  });
  await page.route("**/avatar/standard.png", (route) => route.fulfill({ path: standardImage }));
  await page.route("**/avatar/thinking.png", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.fulfill({ path: thinkingImage });
  });
});

test("first and second thinking transitions render only decoded thinking sprite data", async ({ page }) => {
  await page.goto("/");
  const avatar = page.getByTestId("avatar");
  await expect(avatar).toHaveJSProperty("naturalWidth", 408);
  const decodedImage = () => avatar.evaluate((image) => {
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext("2d");
    context?.drawImage(image, 0, 0);
    const pixels = context?.getImageData(0, 0, canvas.width, canvas.height).data;
    let checksum = 0;
    for (let index = 0; pixels && index < pixels.length; index += 97) {
      checksum = (checksum + pixels[index]) % 1_000_000_007;
    }
    return { width: canvas.width, height: canvas.height, checksum };
  });
  const standardData = await decodedImage();
  const thinkingLoads: Array<{ width: number; height: number; checksum: number }> = [];

  for (let turn = 0; turn < 2; turn += 1) {
    await page.evaluate(() => {
      (window as Window & { __emitTauriEvent(event: string, payload: unknown): void })
        .__emitTauriEvent("avatar-runtime-state", { state: "thinking", backendPending: true });
    });
    await expect(avatar).toHaveAttribute("data-avatar-state", "thinking");
    // `naturalWidth` becomes non-zero only after the browser has decoded the
    // newly selected source, so it is the observable image-load boundary.
    await expect(avatar).toHaveJSProperty("naturalWidth", 1800);
    await expect(avatar).toHaveAttribute("data-avatar-frame", "0");
    await expect(avatar).toHaveCSS("transform", "matrix(1, 0, 0, 1, -77, -6)");
    thinkingLoads.push(await decodedImage());

    await page.evaluate(() => {
      (window as Window & { __emitTauriEvent(event: string, payload: unknown): void })
        .__emitTauriEvent("avatar-runtime-state", { state: "standard", backendPending: false });
    });
    await expect(avatar).toHaveAttribute("data-avatar-state", "standard");
  }

  expect(standardData).toEqual({ width: 408, height: 612, checksum: expect.any(Number) });
  expect(thinkingLoads).toEqual([
    { width: 1800, height: 600, checksum: expect.any(Number) },
    { width: 1800, height: 600, checksum: expect.any(Number) },
  ]);
  expect(thinkingLoads[0].checksum).toBe(thinkingLoads[1].checksum);
  expect(thinkingLoads[0].checksum).not.toBe(standardData.checksum);
});
