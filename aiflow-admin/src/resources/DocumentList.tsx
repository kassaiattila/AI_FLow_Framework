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
import { Chip, IconButton, Stack, Tooltip, ToggleButtonGroup, ToggleButton } from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getResourceSource } from "../dataProvider";

// Detect unprocessed documents: no meaningful vendor name or zero total
function isUnprocessed(record: Record<string, unknown>): boolean {
  const vendor = record.vendor as Record<string, unknown> | undefined;
  const totals = record.totals as Record<string, unknown> | undefined;
  const sourceFile = (record.source_file as string) || "";
  const vendorName = (vendor?.name as string) || "";
  const grossTotal = (totals?.gross_total as number) || 0;

  // If vendor name looks like a filename fragment (matches source_file prefix), it's not real
  const baseName = sourceFile.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
  const vendorLooksLikeFile = vendorName && baseName.toLowerCase().startsWith(vendorName.toLowerCase().slice(0, 10));

  return grossTotal === 0 && (!vendorName || vendorLooksLikeFile);
}

// Clean vendor name: if it looks like a filename fragment, return empty
function cleanVendorName(record: Record<string, unknown>): string {
  const vendor = record.vendor as Record<string, unknown> | undefined;
  const sourceFile = (record.source_file as string) || "";
  const vendorName = (vendor?.name as string) || "";
  if (!vendorName) return "-";

  const baseName = sourceFile.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ");
  if (baseName.toLowerCase().startsWith(vendorName.toLowerCase().slice(0, 10))) {
    return "-";
  }
  return vendorName;
}

type FilterMode = "all" | "processed";

const ListActions = ({ filterMode, onFilterModeChange }: { filterMode: FilterMode; onFilterModeChange: (mode: FilterMode) => void }) => {
  const translate = useTranslate();
  const source = getResourceSource("documents");
  return (
    <TopToolbar>
      <ToggleButtonGroup
        size="small"
        value={filterMode}
        exclusive
        onChange={(_, v) => v && onFilterModeChange(v)}
        sx={{ mr: 1, "& .MuiToggleButton-root": { px: 1.5, py: 0.25, fontSize: "0.75rem" } }}
      >
        <ToggleButton value="all">{translate("aiflow.documents.filterAll")}</ToggleButton>
        <ToggleButton value="processed">{translate("aiflow.documents.filterProcessed")}</ToggleButton>
      </ToggleButtonGroup>
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

const documentFilters = [
  <SearchInput source="q" alwaysOn />,
  <TextInput source="vendor.name" label="Vendor" />,
  <TextInput source="header.invoice_number" label="Invoice #" />,
];

export const DocumentList = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const [filterMode, setFilterMode] = useState<FilterMode>("all");

  return (
    <List
      title={translate("aiflow.documents.title")}
      perPage={25}
      sort={{ field: "header.invoice_date", order: "DESC" }}
      actions={<ListActions filterMode={filterMode} onFilterModeChange={setFilterMode} />}
      filters={documentFilters}
      filter={filterMode === "processed" ? { _processed: true } : undefined}
    >
      <Datagrid
        rowClick={(id) => `/documents/${encodeURIComponent(String(id))}/verify`}
        bulkActionButtons={false}
        rowSx={(record: Record<string, unknown>) =>
          isUnprocessed(record)
            ? { opacity: 0.5, bgcolor: "action.hover" }
            : undefined
        }
      >
        <TextField source="source_file" label={translate("aiflow.documents.file")} />

        {/* Vendor — cleaned name */}
        <FunctionField
          source="vendor.name"
          label={translate("aiflow.documents.vendor")}
          render={(record: Record<string, unknown>) => cleanVendorName(record)}
        />

        <TextField source="header.invoice_number" label={translate("aiflow.documents.invoiceNumber")} />
        <TextField source="header.invoice_date" label={translate("aiflow.documents.date")} />
        <TextField source="header.currency" label={translate("aiflow.documents.currency")} />

        {/* Gross total — show "—" for unprocessed */}
        <FunctionField
          source="totals.gross_total"
          label={translate("aiflow.documents.grossTotal")}
          render={(record: Record<string, unknown>) => {
            if (isUnprocessed(record)) return <span style={{ color: "inherit" }}>—</span>;
            const totals = record.totals as Record<string, unknown> | undefined;
            const val = (totals?.gross_total as number) || 0;
            return val.toLocaleString("hu-HU", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
          }}
        />

        {/* Status chip */}
        <FunctionField
          sortBy="validation.is_valid"
          label={translate("aiflow.documents.valid")}
          render={(record: Record<string, unknown>) => {
            if (isUnprocessed(record)) {
              return <Chip label={translate("aiflow.documents.unprocessed")} size="small" variant="outlined" />;
            }
            const valid = (record.validation as Record<string, unknown>)?.is_valid;
            return (
              <Chip
                label={valid ? "OK" : "!"}
                color={valid ? "success" : "error"}
                size="small"
              />
            );
          }}
        />

        {/* Quick actions */}
        <FunctionField
          label=""
          render={(record: Record<string, unknown>) => (
            <Stack direction="row" spacing={0}>
              <Tooltip title={translate("aiflow.verification.verify")}>
                <IconButton
                  size="small"
                  color="primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/documents/${encodeURIComponent(String(record.id))}/verify`);
                  }}
                >
                  <VerifiedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={translate("ra.message.details")}>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/documents/${encodeURIComponent(String(record.id))}/show`);
                  }}
                >
                  <InfoOutlinedIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          )}
        />
      </Datagrid>
    </List>
  );
};
