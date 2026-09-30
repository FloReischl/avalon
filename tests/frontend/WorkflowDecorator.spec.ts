import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowDecorator from "../../frontend/src/components/WorkflowDecorator.vue";

describe("WorkflowDecorator", () => {
  it("shows the running fallback without progress", () => {
    const wrapper = mount(WorkflowDecorator, {
      props: { execution: { id: 1, state: "running", progress_content: null } },
    });
    expect(wrapper.text()).toContain("Workflow läuft …");
  });

  it("shows the completed fallback without progress", () => {
    const wrapper = mount(WorkflowDecorator, {
      props: { execution: { id: 1, state: "completed", progress_content: null } },
    });
    expect(wrapper.text()).toContain("Workflow abgeschlossen");
  });

  it.each(["running", "completed"] as const)(
    "shows all progress entries for %s", (state) => {
      const wrapper = mount(WorkflowDecorator, {
        props: { execution: { id: 1, state, progress_content: ["Podcast 1 fertig", "Podcast 2 läuft"] } },
      });
      expect(wrapper.findAll("li").map((item) => item.text())).toEqual([
        "Podcast 1 fertig", "Podcast 2 läuft",
      ]);
    },
  );
});
