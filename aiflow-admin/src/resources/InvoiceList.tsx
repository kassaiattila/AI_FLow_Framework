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

const invoiceFilters = [
  <SearchInput source="q" alwaysOn />,
  <TextInput source="vendor.name" label="Vendor" />,
  <TextInput source="header.invoice_number" label="Invoice #" />,
];

const ListActions = () => {
  const translate = useTranslate();
  const source = getResourceSource("invoices");
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

export const InvoiceList = () => {
  const translate = useTranslate();
  return (
    <List
      title={translate("aiflow.invoices.title")}
      perPage={25}
      sort={{ field: "header.invoice_date", order: "DESC" }}
      actions={<ListActions />}
      filters={invoiceFilters}
    >
      <Datagrid
        rowClick={(id) => `/invoices/${encodeURIComponent(String(id))}/verify`}
        bulkActionButtons={false}
      >
        <TextField source="source_file" label={translate("aiflow.invoices.file")} />
        <TextField source="vendor.name" label={translate("aiflow.invoices.vendor")} />
        <TextField source="header.invoice_number" label={translate("aiflow.invoices.invoiceNumber")} />
        <TextField source="header.invoice_date" label={translate("aiflow.invoices.date")} />
        <TextField source="header.currency" label={translate("aiflow.invoices.currency")} />
        <NumberField
          source="totals.gross_total"
          label={translate("aiflow.invoices.grossTotal")}
          options={{ minimumFractionDigits: 0, maximumFractionDigits: 0 }}
        />
        <FunctionField
          sortBy="validation.is_valid"
          label={translate("aiflow.invoices.valid")}
          render={(record: { validation?: { is_valid: boolean } }) => (
            <Chip
              label={record.validation?.is_valid ? "OK" : "!"}
              color={record.validation?.is_valid ? "success" : "error"}
              size="small"
            />
          )}
        />
      </Datagrid>
    </List>
  );
};
