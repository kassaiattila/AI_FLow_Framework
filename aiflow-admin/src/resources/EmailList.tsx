import {
  List,
  Datagrid,
  TextField,
  FunctionField,
  useTranslate,
  TextInput,
  TopToolbar,
  FilterButton,
  SearchInput,
} from "react-admin";
import { Chip } from "@mui/material";
import { getResourceSource } from "../dataProvider";

const emailFilters = [
  <SearchInput source="q" alwaysOn />,
  <TextInput source="sender" label="Sender" />,
  <TextInput source="subject" label="Subject" />,
];

const ListActions = () => {
  const translate = useTranslate();
  const source = getResourceSource("emails");
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

const PRIORITY_COLOR: Record<string, "error" | "warning" | "info" | "success" | "default"> = {
  critical: "error",
  high: "warning",
  medium: "info",
  low: "success",
  normal: "default",
};

export const EmailList = () => {
  const translate = useTranslate();
  return (
    <List
      title={translate("aiflow.emails.title")}
      perPage={25}
      sort={{ field: "received_date", order: "DESC" }}
      actions={<ListActions />}
      filters={emailFilters}
    >
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <TextField source="sender" label={translate("aiflow.emails.sender")} />
        <TextField source="subject" label={translate("aiflow.emails.subject")} />
        <FunctionField
          sortBy="intent.intent_display_name"
          label={translate("aiflow.emails.intent")}
          render={(record: { intent?: { intent_display_name: string } | null }) =>
            record.intent?.intent_display_name || "-"
          }
        />
        <FunctionField
          sortBy="intent.confidence"
          label={translate("aiflow.emails.confidence")}
          render={(record: { intent?: { confidence: number } | null }) =>
            record.intent?.confidence != null
              ? `${(record.intent.confidence * 100).toFixed(0)}%`
              : "-"
          }
        />
        <FunctionField
          sortBy="priority.priority_name"
          label={translate("aiflow.emails.priority")}
          render={(record: { priority?: { priority_name: string; priority_display_name: string } | null }) =>
            record.priority ? (
              <Chip
                label={record.priority.priority_display_name}
                color={PRIORITY_COLOR[record.priority.priority_name] || "default"}
                size="small"
              />
            ) : (
              "-"
            )
          }
        />
        <FunctionField
          sortBy="received_date"
          label={translate("aiflow.emails.received")}
          render={(record: { received_date: string }) =>
            record.received_date ? new Date(record.received_date).toLocaleString() : "-"
          }
        />
        <FunctionField
          sortBy="attachment_count"
          label={translate("aiflow.emails.attachments")}
          render={(record: { attachment_count: number }) =>
            record.attachment_count > 0 ? `${record.attachment_count}` : "-"
          }
        />
      </Datagrid>
    </List>
  );
};
