<script setup lang="ts">
import { computed, shallowRef } from "vue";
import { AgGridVue } from "ag-grid-vue3";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
  type ColDef,
  type GridApi,
  type GridReadyEvent,
  type CellValueChangedEvent,
  type IRowNode,
  type SelectionChangedEvent,
} from "ag-grid-community";
import type { ConfirmationGridModel } from "./confirmationGridModel";

ModuleRegistry.registerModules([AllCommunityModule]);

const props = defineProps<{
  model: ConfirmationGridModel;
  selectedRowIds: string[];
}>();
const emit = defineEmits<{
  "update:selectedRowIds": [ids: string[]];
  "cell-value-changed": [rowId: string, columnId: string, value: unknown];
}>();
const api = shallowRef<GridApi>();

const columnDefs = computed<ColDef[]>(() => props.model.columns.map((column) => ({
  colId: column.id,
  field: column.id,
  headerName: column.label,
  minWidth: column.minWidth,
  flex: column.flex,
  sortable: true,
  filter: true,
  hide: column.visible === false,
  editable: column.editable ?? false,
  suppressMovable: true,
  cellDataType: column.cellDataType,
  cellEditor: column.cellEditor,
  valueParser: column.valueParser ? (params) => column.valueParser?.(params.newValue) : undefined,
  cellClassRules: column.invalid
    ? { "confirmation-grid__cell--invalid": (params) => column.invalid?.(params.data) ?? false }
    : undefined,
}))); 
const rowData = computed(() => props.model.rows.map((row) => ({ id: row.id, ...row.cells })));
const rowSelection = { mode: "multiRow" as const, checkboxes: true, headerCheckbox: true, enableClickSelection: true };

function selectionChanged(event: SelectionChangedEvent) {
  emit("update:selectedRowIds", event.api.getSelectedRows().map((row) => row.id));
}
function gridReady(event: GridReadyEvent) { api.value = event.api; }
function cellValueChanged(event: CellValueChangedEvent) {
  const rowId = event.data?.id;
  const columnId = event.column.getColId();
  if (typeof rowId === "string") emit("cell-value-changed", rowId, columnId, event.newValue);
}
function selectVisible(predicate: (row: Record<string, unknown>) => boolean = () => true) {
  api.value?.forEachNodeAfterFilter((node: IRowNode) => {
    if (node.data && predicate(node.data as Record<string, unknown>)) node.setSelected(true);
  });
}
function deselectAll() { api.value?.deselectAll(); }
export interface ConfirmationGridHandle {
  selectVisible: (predicate?: (row: Record<string, unknown>) => boolean) => void;
  deselectAll: () => void;
}
defineExpose<ConfirmationGridHandle>({ selectVisible, deselectAll });
</script>

<template>
  <AgGridVue
    class="confirmation-grid"
    :theme="themeQuartz"
    :column-defs="columnDefs"
    :row-data="rowData"
    :row-selection="rowSelection"
    :get-row-id="(params) => params.data.id"
    @grid-ready="gridReady"
    @selection-changed="selectionChanged"
    @cell-value-changed="cellValueChanged"
  />
</template>

<style scoped>
.confirmation-grid { width: 100%; height: 17rem; }
.confirmation-grid :deep(.confirmation-grid__cell--invalid) { background: #ffe4e4; outline: 1px solid #b42318; }
</style>
