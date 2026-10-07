/** Avalon-owned data boundary for confirmation tables. */
export interface ConfirmationGridColumn {
  id: string;
  label: string;
  minWidth?: number;
  flex?: number;
  visible?: boolean;
  editable?: boolean;
  cellDataType?: string | boolean;
  cellEditor?: string;
  valueParser?: (value: unknown) => unknown;
}

export interface ConfirmationGridRow {
  id: string;
  cells: Record<string, unknown>;
}

export interface ConfirmationGridModel {
  columns: ConfirmationGridColumn[];
  rows: ConfirmationGridRow[];
}
