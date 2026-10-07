/** Avalon-owned data boundary for confirmation tables. */
export interface ConfirmationGridColumn {
  id: string;
  label: string;
  minWidth?: number;
  flex?: number;
}

export interface ConfirmationGridRow {
  id: string;
  cells: Record<string, string>;
}

export interface ConfirmationGridModel {
  columns: ConfirmationGridColumn[];
  rows: ConfirmationGridRow[];
}
