import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ConfirmationGrid from "../../frontend/src/components/ConfirmationGrid.vue";

describe("ConfirmationGrid", () => {
  const model = {
    columns: [
      { id: "context", label: "Context", minWidth: 120, flex: 1 },
      { id: "approved", label: "Approved", minWidth: 100 },
    ],
    rows: [
      { id: "permission-1", cells: { context: "web", approved: "✓" } },
      { id: "permission-2", cells: { context: "file", approved: "" } },
    ],
  };

  it("maps the Avalon model to AG Grid columns, rows, and stable row ids", async () => {
    const wrapper = mount(ConfirmationGrid, { props: { model, selectedRowIds: [] } });
    await flushPromises();

    expect(wrapper.get('[role="columnheader"][col-id="context"]').text()).toContain("Context");
    expect(wrapper.get('[role="columnheader"][col-id="approved"]').text()).toContain("Approved");
    expect(wrapper.get('[role="row"][row-id="permission-1"]').text()).toContain("web");
    expect(wrapper.get('[role="row"][row-id="permission-2"]').text()).toContain("file");
  });

  it("forwards AG Grid row selection as Avalon row ids", async () => {
    const wrapper = mount(ConfirmationGrid, { props: { model, selectedRowIds: [] } });
    await flushPromises();
    const checkbox = wrapper.find('[role="row"][row-id="permission-2"] input[type="checkbox"]');

    await checkbox.trigger("click");
    await flushPromises();

    expect(wrapper.emitted("update:selectedRowIds")).toEqual([
      [["permission-2"]],
    ]);
  });
});
