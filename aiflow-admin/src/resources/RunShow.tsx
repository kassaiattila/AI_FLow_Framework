import {
  Show, SimpleShowLayout, TextField, NumberField,
  FunctionField, useTranslate, useRecordContext,
} from "react-admin";
import { Chip, Typography, Box, Divider, Stack } from "@mui/material";
import { StepTimeline, type TimelineStep } from "../components/StepTimeline";

const StepsTimeline = () => {
  const record = useRecordContext();
  if (!record?.steps) return null;
  return <StepTimeline steps={record.steps as TimelineStep[]} />;
};

export const RunShow = () => {
  const translate = useTranslate();
  return (
    <Show>
      <SimpleShowLayout>
        <TextField source="run_id" label="Run ID" />
        <TextField source="skill_name" label={translate("aiflow.runs.skill")} />
        <FunctionField
          label={translate("aiflow.runs.status")}
          render={(record: { status: string }) => (
            <Chip label={record.status} color={record.status === "completed" ? "success" : "error"} size="small" />
          )}
        />
        <FunctionField
          label={translate("aiflow.runs.started")}
          render={(record: { started_at: string }) =>
            record.started_at ? new Date(record.started_at).toLocaleString() : "-"
          }
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
        <TextField source="input_summary" label="Input" />
        <TextField source="output_summary" label="Output" />

        <Divider sx={{ my: 2 }} />

        <Box>
          <Typography variant="h6" gutterBottom>
            {translate("aiflow.pipeline.title")}
          </Typography>
          <StepsTimeline />
        </Box>
      </SimpleShowLayout>
    </Show>
  );
};
