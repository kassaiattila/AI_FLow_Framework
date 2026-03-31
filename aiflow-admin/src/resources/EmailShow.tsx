import {
  Show,
  SimpleShowLayout,
  TextField,
  FunctionField,
  useTranslate,
} from "react-admin";
import { Typography, Divider, Chip, Stack, Card, CardContent, Box, Button } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { useNavigate } from "react-router-dom";

export const EmailShow = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  return (
    <Show title={translate("aiflow.emails.detail")}>
      <SimpleShowLayout>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/emails")} size="small" sx={{ mb: 1, alignSelf: "flex-start" }}>
          {translate("ra.action.back")}
        </Button>
        {/* Email header */}
        <TextField source="sender" label={translate("aiflow.emails.sender")} />
        <TextField source="subject" label={translate("aiflow.emails.subject")} />
        <FunctionField
          label={translate("aiflow.emails.received")}
          render={(record: { received_date: string }) =>
            record.received_date ? new Date(record.received_date).toLocaleString() : "-"
          }
        />

        <Divider sx={{ my: 2 }} />

        {/* Body */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.emails.body")}
        </Typography>
        <FunctionField
          render={(record: { body?: string }) => (
            <Card variant="outlined">
              <CardContent>
                <Typography
                  variant="body2"
                  sx={{ whiteSpace: "pre-wrap", fontFamily: "monospace" }}
                >
                  {record.body || "-"}
                </Typography>
              </CardContent>
            </Card>
          )}
        />

        <Divider sx={{ my: 2 }} />

        {/* Intent */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.emails.intentSection")}
        </Typography>
        <FunctionField
          label={translate("aiflow.emails.intent")}
          render={(record: {
            intent?: {
              intent_display_name: string;
              confidence: number;
              method: string;
              reasoning: string;
              sklearn_intent?: string | null;
              sklearn_confidence?: number;
              llm_intent?: string | null;
              llm_confidence?: number;
            } | null;
          }) => {
            const i = record.intent;
            if (!i) return <Typography color="text.secondary">-</Typography>;
            return (
              <Stack spacing={1}>
                <Box>
                  <Chip label={i.intent_display_name} color="primary" size="small" />
                  <Chip
                    label={`${(i.confidence * 100).toFixed(0)}%`}
                    size="small"
                    sx={{ ml: 1 }}
                  />
                  <Chip label={i.method} variant="outlined" size="small" sx={{ ml: 1 }} />
                </Box>
                {i.sklearn_intent && (
                  <Typography variant="body2">
                    sklearn: {i.sklearn_intent} ({((i.sklearn_confidence || 0) * 100).toFixed(0)}%)
                  </Typography>
                )}
                {i.llm_intent && (
                  <Typography variant="body2">
                    LLM: {i.llm_intent} ({((i.llm_confidence || 0) * 100).toFixed(0)}%)
                  </Typography>
                )}
                {i.reasoning && (
                  <Typography variant="body2" color="text.secondary">
                    {i.reasoning}
                  </Typography>
                )}
              </Stack>
            );
          }}
        />

        <Divider sx={{ my: 2 }} />

        {/* Entities */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.emails.entitiesSection")}
        </Typography>
        <FunctionField
          render={(record: {
            entities?: { entities: Array<{ entity_type: string; value: string; confidence: number; extraction_method: string }> } | null;
          }) => {
            const entities = record.entities?.entities || [];
            if (entities.length === 0)
              return <Typography color="text.secondary">-</Typography>;
            return (
              <Stack direction="row" flexWrap="wrap" gap={1}>
                {entities.map((e, i) => (
                  <Chip
                    key={i}
                    label={`${e.entity_type}: ${e.value}`}
                    size="small"
                    variant="outlined"
                    title={`${(e.confidence * 100).toFixed(0)}% (${e.extraction_method})`}
                  />
                ))}
              </Stack>
            );
          }}
        />

        <Divider sx={{ my: 2 }} />

        {/* Priority & Routing */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.emails.routingSection")}
        </Typography>
        <FunctionField
          label={translate("aiflow.emails.priority")}
          render={(record: { priority?: { priority_display_name: string; sla_hours: number; matched_rule: string } | null }) => {
            const p = record.priority;
            if (!p) return <Typography color="text.secondary">-</Typography>;
            return (
              <Stack spacing={0.5}>
                <Box>
                  <Chip label={p.priority_display_name} color="warning" size="small" />
                  <Typography variant="body2" component="span" sx={{ ml: 1 }}>
                    SLA: {p.sla_hours}h
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {translate("aiflow.emails.rule")}: {p.matched_rule}
                </Typography>
              </Stack>
            );
          }}
        />
        <FunctionField
          label={translate("aiflow.emails.routing")}
          render={(record: {
            routing?: {
              queue_name: string;
              department_name: string;
              department_email: string;
              notes: string;
            } | null;
          }) => {
            const r = record.routing;
            if (!r) return <Typography color="text.secondary">-</Typography>;
            return (
              <Stack spacing={0.5}>
                <Typography variant="body2">
                  {translate("aiflow.emails.queue")}: {r.queue_name}
                </Typography>
                <Typography variant="body2">
                  {translate("aiflow.emails.department")}: {r.department_name} ({r.department_email})
                </Typography>
                {r.notes && (
                  <Typography variant="body2" color="text.secondary">
                    {r.notes}
                  </Typography>
                )}
              </Stack>
            );
          }}
        />

        <Divider sx={{ my: 2 }} />

        {/* Attachments */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.emails.attachmentsSection")}
        </Typography>
        <FunctionField
          render={(record: {
            attachment_summaries?: Array<{
              filename: string;
              mime_type: string;
              size_bytes: number;
              document_type: string;
              processor_used: string;
            }>;
          }) => {
            const atts = record.attachment_summaries || [];
            if (atts.length === 0)
              return <Typography color="text.secondary">-</Typography>;
            return (
              <Stack spacing={1}>
                {atts.map((a, i) => (
                  <Card key={i} variant="outlined">
                    <CardContent sx={{ py: 1, "&:last-child": { pb: 1 } }}>
                      <Typography variant="body2" fontWeight="bold">
                        {a.filename}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {a.mime_type} | {(a.size_bytes / 1024).toFixed(1)} KB | {a.document_type} | {a.processor_used}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            );
          }}
        />

        <Divider sx={{ my: 2 }} />

        {/* Processing metadata */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.emails.processing")}
        </Typography>
        <FunctionField
          label={translate("aiflow.emails.processingTime")}
          render={(record: { processing_time_ms?: number }) =>
            record.processing_time_ms != null ? `${record.processing_time_ms}ms` : "-"
          }
        />
        <TextField source="pipeline_version" label={translate("aiflow.emails.pipelineVersion")} />
      </SimpleShowLayout>
    </Show>
  );
};
