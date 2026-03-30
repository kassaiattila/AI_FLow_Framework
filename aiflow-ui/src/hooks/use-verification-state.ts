"use client";

import { useReducer, useCallback, useMemo } from "react";
import type {
  DataPoint,
  DocumentMeta,
  InvoiceVerificationData,
} from "@/lib/verification-types";

// --- State ---

export interface AuditEntry {
  timestamp: string;
  action: string;
  field_id: string | null;
  old_value: string | null;
  new_value: string | null;
}

interface VerificationState {
  dataPoints: DataPoint[];
  documentMeta: DocumentMeta | null;
  pageDimensions: { width: number; height: number };
  hoveredPointId: string | null;
  selectedPointId: string | null;
  editingPointId: string | null;
  editBuffer: string;
  originalValues: Record<string, string>;
  auditLog: AuditEntry[];
}

const INITIAL_STATE: VerificationState = {
  dataPoints: [],
  documentMeta: null,
  pageDimensions: { width: 595, height: 842 },
  hoveredPointId: null,
  selectedPointId: null,
  editingPointId: null,
  editBuffer: "",
  originalValues: {},
  auditLog: [],
};

// --- Actions ---

type Action =
  | { type: "LOAD_DATA"; payload: InvoiceVerificationData }
  | { type: "HOVER_POINT"; payload: string | null }
  | { type: "SELECT_POINT"; payload: string }
  | { type: "START_EDIT"; payload: string }
  | { type: "EDIT_CHANGE"; payload: string }
  | { type: "COMMIT_EDIT" }
  | { type: "CANCEL_EDIT" }
  | { type: "CONFIRM_POINT"; payload: string }
  | { type: "CONFIRM_ALL" }
  | { type: "RESET" };

function reducer(state: VerificationState, action: Action): VerificationState {
  switch (action.type) {
    case "LOAD_DATA": {
      const d = action.payload;
      const originals: Record<string, string> = {};
      for (const dp of d.data_points) {
        originals[dp.id] = dp.extracted_value;
      }
      return {
        ...INITIAL_STATE,
        dataPoints: d.data_points.map((dp) => ({
          ...dp,
          current_value: dp.extracted_value,
          status: "auto" as const,
        })),
        documentMeta: d.document_meta,
        pageDimensions: d.page_dimensions,
        originalValues: originals,
      };
    }

    case "HOVER_POINT":
      return { ...state, hoveredPointId: action.payload };

    case "SELECT_POINT":
      return { ...state, selectedPointId: action.payload };

    case "START_EDIT": {
      const pt = state.dataPoints.find((p) => p.id === action.payload);
      return {
        ...state,
        editingPointId: action.payload,
        editBuffer: pt?.current_value ?? "",
        selectedPointId: action.payload,
      };
    }

    case "EDIT_CHANGE":
      return { ...state, editBuffer: action.payload };

    case "COMMIT_EDIT": {
      if (!state.editingPointId) return state;
      const editId = state.editingPointId;
      const original = state.originalValues[editId] ?? "";
      const oldVal = state.dataPoints.find((dp) => dp.id === editId)?.current_value ?? "";
      const newValue = state.editBuffer;
      const ts = new Date().toISOString();
      return {
        ...state,
        dataPoints: state.dataPoints.map((dp) =>
          dp.id === editId
            ? {
                ...dp,
                current_value: newValue,
                status: newValue !== original ? "corrected" : "auto",
              }
            : dp
        ),
        editingPointId: null,
        editBuffer: "",
        auditLog: oldVal !== newValue
          ? [...state.auditLog, { timestamp: ts, action: "edit", field_id: editId, old_value: oldVal, new_value: newValue }]
          : state.auditLog,
      };
    }

    case "CANCEL_EDIT":
      return { ...state, editingPointId: null, editBuffer: "" };

    case "CONFIRM_POINT":
      return {
        ...state,
        dataPoints: state.dataPoints.map((dp) =>
          dp.id === action.payload ? { ...dp, status: "confirmed" } : dp
        ),
        auditLog: [...state.auditLog, { timestamp: new Date().toISOString(), action: "confirm", field_id: action.payload, old_value: null, new_value: null }],
      };

    case "CONFIRM_ALL":
      return {
        ...state,
        dataPoints: state.dataPoints.map((dp) => ({
          ...dp,
          status: "confirmed",
        })),
        auditLog: [...state.auditLog, { timestamp: new Date().toISOString(), action: "confirm_all", field_id: null, old_value: null, new_value: `${state.dataPoints.length} fields` }],
      };

    case "RESET":
      return {
        ...state,
        dataPoints: state.dataPoints.map((dp) => ({
          ...dp,
          current_value: state.originalValues[dp.id] ?? dp.extracted_value,
          status: "auto",
        })),
        editingPointId: null,
        editBuffer: "",
        selectedPointId: null,
        auditLog: [...state.auditLog, { timestamp: new Date().toISOString(), action: "reset", field_id: null, old_value: null, new_value: null }],
      };

    default:
      return state;
  }
}

// --- Hook ---

export function useVerificationState() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);

  const loadData = useCallback(
    (data: InvoiceVerificationData) =>
      dispatch({ type: "LOAD_DATA", payload: data }),
    []
  );
  const hoverPoint = useCallback(
    (id: string | null) => dispatch({ type: "HOVER_POINT", payload: id }),
    []
  );
  const selectPoint = useCallback(
    (id: string) => dispatch({ type: "SELECT_POINT", payload: id }),
    []
  );
  const startEdit = useCallback(
    (id: string) => dispatch({ type: "START_EDIT", payload: id }),
    []
  );
  const editChange = useCallback(
    (value: string) => dispatch({ type: "EDIT_CHANGE", payload: value }),
    []
  );
  const commitEdit = useCallback(
    () => dispatch({ type: "COMMIT_EDIT" }),
    []
  );
  const cancelEdit = useCallback(
    () => dispatch({ type: "CANCEL_EDIT" }),
    []
  );
  const confirmPoint = useCallback(
    (id: string) => dispatch({ type: "CONFIRM_POINT", payload: id }),
    []
  );
  const confirmAll = useCallback(
    () => dispatch({ type: "CONFIRM_ALL" }),
    []
  );
  const reset = useCallback(() => dispatch({ type: "RESET" }), []);

  const stats = useMemo(() => {
    const total = state.dataPoints.length;
    const auto = state.dataPoints.filter((p) => p.status === "auto").length;
    const corrected = state.dataPoints.filter(
      (p) => p.status === "corrected"
    ).length;
    const confirmed = state.dataPoints.filter(
      (p) => p.status === "confirmed"
    ).length;
    return { total, auto, corrected, confirmed };
  }, [state.dataPoints]);

  return {
    ...state,
    stats,
    loadData,
    hoverPoint,
    selectPoint,
    startEdit,
    editChange,
    commitEdit,
    cancelEdit,
    confirmPoint,
    confirmAll,
    reset,
  };
}
