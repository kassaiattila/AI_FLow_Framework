/**
 * AIFlow DataTable — powered by TanStack Table (React Table v8).
 * Headless table with Tailwind styling: sort, filter, pagination, multi-select.
 */

import { useState, useMemo, useEffect, useRef } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
  type RowSelectionState,
} from "@tanstack/react-table";
import { useTranslate } from "../lib/i18n";

// --- Public API ---

export interface Column<T> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (item: T) => React.ReactNode;
  getValue?: (item: T) => string | number | null;
  width?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  searchable?: boolean;
  searchKeys?: string[];
  pageSize?: number;
  onRowClick?: (item: T) => void;
  emptyMessageKey?: string;
  loading?: boolean;
  /** Enable row selection checkboxes. Provide a unique key field (default: "id"). */
  selectable?: boolean;
  /** Called whenever the set of selected rows changes. */
  onSelectionChange?: (selectedItems: T[]) => void;
  /** Externally controlled selection state — cleared when set to 0 (e.g. after bulk action). */
  clearSelection?: number;
}

// --- Helpers ---

function getNestedValue(obj: unknown, path: string): unknown {
  return path.split(".").reduce((curr: unknown, key: string) => {
    if (curr && typeof curr === "object")
      return (curr as Record<string, unknown>)[key];
    return undefined;
  }, obj);
}

// --- Checkbox ---

function IndeterminateCheckbox({
  indeterminate,
  checked,
  onChange,
  ariaLabel,
}: {
  indeterminate?: boolean;
  checked: boolean;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  ariaLabel: string;
}) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={onChange}
      ref={(el) => {
        if (el) el.indeterminate = !!indeterminate;
      }}
      aria-label={ariaLabel}
      className="h-4 w-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800"
    />
  );
}

// --- Component ---

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  searchable = true,
  searchKeys,
  pageSize = 10,
  onRowClick,
  emptyMessageKey = "aiflow.common.empty",
  loading = false,
  selectable = false,
  onSelectionChange,
  clearSelection,
}: DataTableProps<T>) {
  const translate = useTranslate();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  // Clear selection when clearSelection counter changes
  useEffect(() => {
    if (clearSelection !== undefined) setRowSelection({});
  }, [clearSelection]);

  // Notify parent of selection changes — use refs to avoid re-render loops.
  // data is NOT in deps: re-notification only fires on actual selection change.
  const onSelectionChangeRef = useRef(onSelectionChange);
  onSelectionChangeRef.current = onSelectionChange;
  const dataRef = useRef(data);
  dataRef.current = data;

  useEffect(() => {
    if (!onSelectionChangeRef.current || !selectable) return;
    const selectedIndices = Object.keys(rowSelection).filter(
      (k) => rowSelection[k],
    );
    const selectedItems = selectedIndices
      .map((idx) => dataRef.current[parseInt(idx)])
      .filter(Boolean);
    onSelectionChangeRef.current(selectedItems);
  }, [rowSelection, selectable]);

  // Build columns with optional checkbox column
  const tanstackColumns = useMemo<ColumnDef<T, unknown>[]>(() => {
    const cols: ColumnDef<T, unknown>[] = [];

    if (selectable) {
      cols.push({
        id: "_select",
        header: ({ table }) => (
          <IndeterminateCheckbox
            checked={table.getIsAllPageRowsSelected()}
            indeterminate={table.getIsSomePageRowsSelected()}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
            ariaLabel="Select all rows"
          />
        ),
        cell: ({ row }) => (
          <IndeterminateCheckbox
            checked={row.getIsSelected()}
            onChange={row.getToggleSelectedHandler()}
            ariaLabel={`Select row ${row.index + 1}`}
          />
        ),
        enableSorting: false,
        size: 40,
      });
    }

    cols.push(
      ...columns.map((col) => ({
        id: col.key,
        accessorFn: (row: T) => {
          if (col.getValue) return col.getValue(row);
          return getNestedValue(row, col.key);
        },
        header: col.label,
        cell: col.render
          ? (info: { row: { original: T } }) => col.render!(info.row.original)
          : (info: { getValue: () => unknown }) => {
              const val = info.getValue();
              return val != null ? String(val) : "—";
            },
        enableSorting: col.sortable !== false,
        size: col.width ? parseInt(col.width) : undefined,
      })),
    );

    return cols;
  }, [columns, selectable]);

  // Custom global filter
  const effectiveSearchKeys = searchKeys ?? columns.map((c) => c.key);
  const globalFilterFn = useMemo(
    () => (row: { original: T }, _columnId: string, filterValue: string) => {
      if (!filterValue) return true;
      const q = filterValue.toLowerCase();
      return effectiveSearchKeys.some((key) => {
        const col = columns.find((c) => c.key === key);
        const val = col?.getValue
          ? col.getValue(row.original)
          : getNestedValue(row.original, key);
        if (val == null) return false;
        return String(val).toLowerCase().includes(q);
      });
    },
    [effectiveSearchKeys, columns],
  );

  const table = useReactTable({
    data,
    columns: tanstackColumns,
    state: { sorting, globalFilter, columnFilters, rowSelection },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    onRowSelectionChange: setRowSelection,
    enableRowSelection: selectable,
    globalFilterFn,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  const selectedCount = Object.values(rowSelection).filter(Boolean).length;

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-900">
        {[1, 2, 3].map((i) => (
          <div key={i} className="mb-3 animate-pulse">
            <div
              className="h-4 rounded bg-gray-200 dark:bg-gray-700"
              style={{ width: `${90 - i * 15}%` }}
            />
          </div>
        ))}
      </div>
    );
  }

  const rows = table.getRowModel().rows;

  return (
    <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      {/* Search + count + selection info */}
      {searchable && (
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3 dark:border-gray-800">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {selectable && selectedCount > 0
              ? `${selectedCount} ${translate("aiflow.common.selected")}`
              : `${table.getFilteredRowModel().rows.length} / ${data.length}`}
          </span>
          <div className="relative">
            <svg
              className="absolute left-2.5 top-2 h-4 w-4 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              placeholder={translate("aiflow.common.search")}
              className="w-52 rounded-lg border border-gray-300 bg-white py-1.5 pl-8 pr-3 text-sm text-gray-700 placeholder-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
            />
          </div>
        </div>
      )}

      {/* Table */}
      {rows.length === 0 ? (
        <div className="flex flex-col items-center py-12 text-center">
          <svg
            className="mb-3 h-10 w-10 text-gray-300 dark:text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {translate(emptyMessageKey)}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr
                  key={headerGroup.id}
                  className="border-b border-gray-100 text-left dark:border-gray-800"
                >
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      onClick={
                        header.column.getCanSort()
                          ? header.column.getToggleSortingHandler()
                          : undefined
                      }
                      className={`px-4 py-3 text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400 ${
                        header.column.getCanSort()
                          ? "cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-200"
                          : ""
                      }`}
                      style={
                        header.column.id === "_select"
                          ? { width: 40 }
                          : header.getSize()
                            ? { width: header.getSize() }
                            : undefined
                      }
                    >
                      {header.column.id === "_select" ? (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )
                      ) : (
                        <span className="inline-flex items-center gap-1">
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          {header.column.getCanSort() && (
                            <span className="text-brand-500">
                              {{ asc: "↑", desc: "↓" }[
                                header.column.getIsSorted() as string
                              ] ?? "↕"}
                            </span>
                          )}
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={
                    onRowClick ? () => onRowClick(row.original) : undefined
                  }
                  className={`border-b border-gray-50 dark:border-gray-800 ${
                    row.getIsSelected()
                      ? "bg-brand-50/50 dark:bg-brand-900/10"
                      : ""
                  } ${onRowClick ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50" : ""}`}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-4 py-3"
                      onClick={
                        cell.column.id === "_select"
                          ? (e) => e.stopPropagation()
                          : undefined
                      }
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between border-t border-gray-100 px-4 py-3 dark:border-gray-800">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            Previous
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Page {table.getState().pagination.pageIndex + 1} of{" "}
            {table.getPageCount()}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
