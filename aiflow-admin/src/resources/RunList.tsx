import {
  List,
  Datagrid,
  TextField,
  NumberField,
  FunctionField,
  useTranslate,
} from "react-admin";
import { Chip } from "@mui/material";

const STATUS_COLOR: Record<string, "success" | "error" | "info" | "warning" | "default"> = {
  completed: "success",
  failed: "error",
  running: "info",
  pending: "warning",
};

export const RunList = () => {
  const translate = useTranslate();
  return (
    <List title={translate("aiflow.runs.title")} perPage={25} sort={{ field: "started_at", order: "DESC" }}>
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="run_id" label="Run ID" />
        <TextField source="skill_name" label={translate("aiflow.runs.skill")} />
        <FunctionField
          label={translate("aiflow.runs.status")}
          render={(record: { status: string }) => (
            <Chip label={record.status} color={STATUS_COLOR[record.status] || "default"} size="small" />
          )}
        />
        <FunctionField
          label={translate("aiflow.runs.duration")}
          render={(record: { total_duration_ms: number }) =>
            record.total_duration_ms < 1000
              ? `${record.total_duration_ms}ms`
              : `${(record.total_duration_ms / 1000).toFixed(1)}s`
          }
        />
        <NumberField source="total_cost_usd" label={translate("aiflow.runs.cost")} options={{ style: "currency", currency: "USD", minimumFractionDigits: 4 }} />
        <TextField source="started_at" label={translate("aiflow.runs.started")} />
      </Datagrid>
    </List>
  );
};
