<script setup lang="ts">
import { computed } from "vue";
import { AgGridVue } from "ag-grid-vue3";
import {
  AllCommunityModule,
  ModuleRegistry,
  themeQuartz,
  type ColDef,
  type SelectionChangedEvent,
} from "ag-grid-community";
import type { ConfirmationGridModel } from "./confirmationGridModel";

ModuleRegistry.registerModules([AllCommunityModule]);

const props = defineProps<{
  model: ConfirmationGridModel;
  selectedRowIds: string[];
}>();
const emit = defineEmits<{ "update:selectedRowIds": [ids: string[]] }>();

const columnDefs = computed<ColDef[]>(() => props.model.columns.map((column) => ({
  colId: column.id,
  field: column.id,
  headerName: column.label,
  minWidth: column.minWidth,
  flex: column.flex,
  sortable: true,
}))); 
const rowData = computed(() => props.model.rows.map((row) => ({ id: row.id, ...row.cells })));
const rowSelection = { mode: "multiRow" as const, checkboxes: true, headerCheckbox: true, enableClickSelection: false };

function selectionChanged(event: SelectionChangedEvent) {
  emit("update:selectedRowIds", event.api.getSelectedRows().map((row) => row.id));
}
</script>

<template>
  <AgGridVue
    class="confirmation-grid"
    :theme="themeQuartz"
    :column-defs="columnDefs"
    :row-data="rowData"
    :row-selection="rowSelection"
    :get-row-id="(params) => params.data.id"
    @selection-changed="selectionChanged"
  />
</template>

<style scoped>
.confirmation-grid { width: 100%; height: 17rem; }
</style>
