import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  openExternalLinkMock,
} = vi.hoisted(() => ({
  openExternalLinkMock: vi.fn(),
}));

vi.mock("../../frontend/src/services/externalLinks", () => ({
  openExternalLink: openExternalLinkMock,
}));

import MarkdownMessage from "../../frontend/src/components/MarkdownMessage.vue";

describe("MarkdownMessage", () => {
  beforeEach(() => {
    openExternalLinkMock.mockReset();
  });

  it("renders standard Markdown and keeps raw HTML escaped", () => {
    const wrapper = mount(MarkdownMessage, {
      props: {
        content: [
          "# Überschrift",
          "",
          "**fett**",
          "",
          "<script>alert('nope')</script>",
          "",
          "| A | B |",
          "| - | - |",
          "| 1 | 2 |",
        ].join("\n"),
      },
    });

    expect(wrapper.find("h1").text()).toBe("Überschrift");
    expect(wrapper.find("strong").text()).toBe("fett");
    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.text()).toContain("<script>alert('nope')</script>");
    expect(wrapper.find("table").exists()).toBe(true);
  });

  it("preserves soft line breaks when requested while keeping Markdown active", () => {
    const wrapper = mount(MarkdownMessage, {
      props: {
        content: "Zeile 1\n**Zeile 2**\nZeile 3",
        preserveLineBreaks: true,
      },
    });

    expect(wrapper.findAll("br")).toHaveLength(2);
    expect(wrapper.find("strong").text()).toBe("Zeile 2");
    expect(wrapper.text()).toContain("Zeile 1");
    expect(wrapper.text()).toContain("Zeile 3");
  });

  it("keeps normal Markdown soft-break behavior by default", () => {
    const wrapper = mount(MarkdownMessage, {
      props: {
        content: "Zeile 1\nZeile 2",
      },
    });

    expect(wrapper.find("br").exists()).toBe(false);
  });

  it("renders fenced code with syntax highlighting and a Copy button", () => {

    const wrapper = mount(MarkdownMessage, {
      props: {
        content: "```ts\nconst answer = 42;\n```",
      },
    });

    expect(wrapper.find("code.language-ts").exists()).toBe(true);
    expect(wrapper.find(".hljs-keyword").exists()).toBe(true);
    expect(wrapper.get("[data-copy-code]").text()).toBe("Copy");
  });

  it("exposes the rendered message HTML", () => {
    const wrapper = mount(MarkdownMessage, {
      props: {
        content: "**fett**",
      },
    });

    expect(wrapper.vm.getRenderedHtml()).toContain(
      "<strong>fett</strong>",
    );
  });

  it("copies the original code text", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);

    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    const wrapper = mount(MarkdownMessage, {
      props: {
        content: "```\nconst answer = 42;\n```",
      },
    });

    await wrapper.get("[data-copy-code]").trigger("click");

    expect(writeText).toHaveBeenCalledWith("const answer = 42;\n");
  });

  it("opens Markdown links through the external-link boundary", async () => {
    openExternalLinkMock.mockResolvedValue(undefined);

    const wrapper = mount(MarkdownMessage, {
      props: {
        content: "[Tauri](https://tauri.app/)",
      },
    });

    const link = wrapper.get("a");
    await link.trigger("click");

    expect(openExternalLinkMock).toHaveBeenCalledTimes(1);
    expect(openExternalLinkMock.mock.calls[0][0]).toBe(
      "https://tauri.app/",
    );
  });
});
