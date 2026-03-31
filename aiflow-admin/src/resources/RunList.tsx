import {
  List,
  Datagrid,
  TextField,
  NumberField,
  FunctionField,
  useTranslate,
  TextInput,
  TopToolbar,
  FilterButton,
  SearchInput,
} from "react-admin";
import { Chip } from "@mui/material";
import { getResourceSource } from "../dataProvider";

const STATUS_COLOR: Record<string, "success" | "error" | "info" | "warning" | "default"> = {
  completed: "success",
  failed: "error",
  running: "info",
  pending: "warning",
};

const runFilters = [
  <SearchInput source="q" alwaysOn />,
  <TextInput source="skill_name" label="Skill" />,
  <TextInput source="status" label="Status" />,
];

const ListActions = () => {
  const translate = useTranslate();
  const source = getResourceSource("runs");
  return (
    <TopToolbar>
      <FilterButton />
      {source && (
        <Chip
          label={translate(`aiflow.status.${source}`)}
          color={source === "demo" ? "warning" : "success"}
          size="small"
          variant="outlined"
        />
      )}
    </TopToolbar>
  );
};

export const RunList = () => {
  const translate = useTranslate();
  return (
    <List title={translate("aiflow.runs.title")} perPage={25} sort={{ field: "started_at", order: "DESC" }} actions={<ListActions />} filters={runFilters}>
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="run_id" label="Run ID" />
        <TextField source="skill_name" label={translate("aiflow.runs.skill")} />
        <FunctionField
          sortBy="status"
          label={translate("aiflow.runs.status")}
          render={(record: { status: string }) => (
            <Chip label={record.status} color={STATUS_COLOR[record.status] || "default"} size="small" />
          )}
        />
        <FunctionField
          sortBy="total_duration_ms"
          label={translate("aiflow.runs.duration")}
          render={(record: { total_duration_ms: number }) =>
            record.total_duration_ms < 1000
              ? `${record.total_duration_ms}ms`
              : `${(record.total_duration_ms / 1000).toFixed(1)}s`
          }
        />
        <NumberField source="total_cost_usd" label={translate("aiflow.runs.cost")} options={{ style: "currency", currency: "USD", minimumFractionDigits: 4 }} />
        <FunctionField
          sortBy="started_at"
          label={translate("aiflow.runs.started")}
          render={(record: { started_at: string }) =>
            record.started_at ? new Date(record.started_at).toLocaleString() : "-"
          }
        />
      </Datagrid>
    </List>
  );
};
