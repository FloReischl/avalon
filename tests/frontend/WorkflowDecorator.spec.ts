import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowDecorator from "../../frontend/src/components/WorkflowDecorator.vue";

describe("WorkflowDecorator", () => {
  it("shows the running fallback without progress", () => {
    const wrapper = mount(WorkflowDecorator, {
      props: { execution: { id: 1, workflow_key: "morning-news", state: "running" }, messages: [] },
    });
    expect(wrapper.text()).toContain("Workflow morning-news läuft …");
  });

  it("shows the completed fallback without progress", () => {
    const wrapper = mount(WorkflowDecorator, {
      props: { execution: { id: 1, workflow_key: "morning-news", state: "completed" }, messages: [] },
    });
    expect(wrapper.text()).toContain("Workflow morning-news abgeschlossen");
  });

  it.each(["running", "completed"] as const)(
    "shows all progress entries for %s", (state) => {
      const wrapper = mount(WorkflowDecorator, {
        props: {
          execution: { id: 1, workflow_key: "morning-news", state },
          messages: ["Podcast 1 fertig", "Podcast 2 läuft"],
        },
      });
      expect(wrapper.findAll("li").map((item) => item.text())).toEqual([
        "Podcast 1 fertig", "Podcast 2 läuft",
      ]);
    },
  );
});
