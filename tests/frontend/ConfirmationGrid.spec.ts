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
    wrapper.unmount();
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
    wrapper.unmount();
  });

  it("supports multi-selection by row click as well as checkboxes", async () => {
    const wrapper = mount(ConfirmationGrid, { props: { model, selectedRowIds: [] } });
    await flushPromises();

    await wrapper.get('[role="row"][row-id="permission-2"] [col-id="context"]').trigger("click");
    await flushPromises();

    expect(wrapper.emitted("update:selectedRowIds")).toEqual([
      [["permission-2"]],
    ]);
    wrapper.unmount();
  });

  it("marks only schema-invalid cells and removes the mark after correction", async () => {
    const invalidModel = {
      columns: [{ id: "value", label: "Value", editable: true, invalid: (row: Record<string, unknown>) => row.value === "invalid" }],
      rows: [
        { id: "one", cells: { value: "invalid" } },
        { id: "two", cells: { value: "invalid" } },
        { id: "three", cells: { value: "valid" } },
      ],
    };
    const wrapper = mount(ConfirmationGrid, { props: { model: invalidModel, selectedRowIds: [] } });
    await flushPromises();
    expect(wrapper.get('[role="row"][row-id="one"] [role="gridcell"][col-id="value"]').classes()).toContain("confirmation-grid__cell--invalid");
    expect(wrapper.get('[role="row"][row-id="two"] [role="gridcell"][col-id="value"]').classes()).toContain("confirmation-grid__cell--invalid");
    expect(wrapper.get('[role="row"][row-id="three"] [role="gridcell"][col-id="value"]').classes()).not.toContain("confirmation-grid__cell--invalid");

    await wrapper.setProps({ model: { ...invalidModel, rows: [{ id: "one", cells: { value: "corrected" } }, { id: "two", cells: { value: "invalid" } }, { id: "three", cells: { value: "valid" } }] } });
    await flushPromises();
    expect(wrapper.get('[role="row"][row-id="one"] [role="gridcell"][col-id="value"]').classes()).not.toContain("confirmation-grid__cell--invalid");
    expect(wrapper.get('[role="row"][row-id="two"] [role="gridcell"][col-id="value"]').classes()).toContain("confirmation-grid__cell--invalid");
    wrapper.unmount();
  });
});
