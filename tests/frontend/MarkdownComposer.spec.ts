import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import MarkdownComposer from "../../frontend/src/components/MarkdownComposer.vue";

describe("MarkdownComposer", () => {
  it("renders the Milkdown editor with the composer contract", async () => {
    const wrapper = mount(MarkdownComposer, {
      props: {
        modelValue: "",
        placeholder: "Dein Prompt hier",
      },
    });

    await flushPromises();

    expect(wrapper.get('[data-testid="chat-input"]').attributes(
      "data-placeholder",
    )).toBe("Dein Prompt hier");
    expect(wrapper.find(".milkdown").exists()).toBe(true);
  });

  it("initializes Milkdown from Markdown", async () => {
    const wrapper = mount(MarkdownComposer, {
      props: {
        modelValue: "**Hallo**",
        placeholder: "Dein Prompt hier",
      },
    });

    await flushPromises();

    expect(wrapper.get(".ProseMirror").text()).toContain("Hallo");
    expect(wrapper.find(".ProseMirror strong").text()).toBe("Hallo");
  });

  it("updates Milkdown when the model changes externally", async () => {
    const wrapper = mount(MarkdownComposer, {
      props: {
        modelValue: "Prompt A",
        placeholder: "Dein Prompt hier",
      },
    });

    await flushPromises();

    await wrapper.setProps({
      modelValue: "Prompt B",
    });
    await flushPromises();

    expect(wrapper.get(".ProseMirror").text()).toContain("Prompt B");
    expect(wrapper.get(".ProseMirror").text()).not.toContain("Prompt A");
  });

  it("clears Milkdown when Avalon clears the model", async () => {
    const wrapper = mount(MarkdownComposer, {
      props: {
        modelValue: "Prompt A",
        placeholder: "Dein Prompt hier",
      },
    });

    await flushPromises();

    await wrapper.setProps({
      modelValue: "",
    });
    await flushPromises();

    expect(wrapper.get(".ProseMirror").text()).toBe("");
  });

  it("shows the formatting toolbar only when enabled", async () => {
    const wrapper = mount(MarkdownComposer, {
      props: {
        modelValue: "",
        placeholder: "Dein Prompt hier",
      },
    });

    await flushPromises();

    expect(wrapper.find('[data-testid="markdown-toolbar"]').exists()).toBe(false);

    await wrapper.setProps({
      toolbarEnabled: true,
    });

    expect(wrapper.find('[data-testid="markdown-toolbar"]').exists()).toBe(true);
  });

  it("executes Milkdown formatting commands from the toolbar", async () => {
    const wrapper = mount(MarkdownComposer, {
      props: {
        modelValue: "Hallo",
        placeholder: "Dein Prompt hier",
        toolbarEnabled: true,
      },
    });

    await flushPromises();

    await wrapper.get('[data-testid="format-heading-1"]').trigger("click");
    await flushPromises();

    expect(wrapper.get(".ProseMirror h1").text()).toBe("Hallo");
  });
});