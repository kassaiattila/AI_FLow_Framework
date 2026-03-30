import { Show, SimpleShowLayout, TextField, NumberField, ArrayField, Datagrid, FunctionField, useTranslate } from "react-admin";
import { Chip, Typography, Box } from "@mui/material";

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
        <TextField source="started_at" label={translate("aiflow.runs.started")} />
        <NumberField source="total_duration_ms" label={translate("aiflow.runs.duration")} />
        <NumberField source="total_cost_usd" label={translate("aiflow.runs.cost")} options={{ style: "currency", currency: "USD", minimumFractionDigits: 4 }} />
        <TextField source="input_summary" label="Input" />
        <TextField source="output_summary" label="Output" />

        <Box mt={2}>
          <Typography variant="subtitle2" gutterBottom>{translate("aiflow.runs.steps")}</Typography>
        </Box>
        <ArrayField source="steps">
          <Datagrid bulkActionButtons={false}>
            <TextField source="step_name" label="Step" />
            <FunctionField
              label={translate("aiflow.runs.status")}
              render={(record: { status: string }) => (
                <Chip label={record.status} color={record.status === "completed" ? "success" : "error"} size="small" variant="outlined" />
              )}
            />
            <NumberField source="duration_ms" label="ms" />
            <NumberField source="tokens_used" label="Tokens" />
            <NumberField source="cost_usd" label="Cost" options={{ style: "currency", currency: "USD", minimumFractionDigits: 4 }} />
            <TextField source="output_preview" label="Output" />
          </Datagrid>
        </ArrayField>
      </SimpleShowLayout>
    </Show>
  );
};
