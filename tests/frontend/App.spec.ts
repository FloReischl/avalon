import { flushPromises, mount } from "@vue/test-utils";

import App from "../../frontend/src/App.vue";

describe("App", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the backend health status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", service: "Avalo Backend" }),
      }),
    );

    const wrapper = mount(App);
    await flushPromises();

    expect(wrapper.get('[data-testid="backend-status"]').text()).toBe(
      "Avalo Backend: ok",
    );
  });

  it.todo("sends a text message and renders the complete response");
  it.todo("records and submits a push-to-talk audio clip");
  it.todo("plays synthesized speech for an assistant response");
});
