import {
  Show,
  SimpleShowLayout,
  TextField,
  NumberField,
  BooleanField,
  ArrayField,
  Datagrid,
  FunctionField,
  useTranslate,
  Labeled,
  useRecordContext,
  TopToolbar,
} from "react-admin";
import { Typography, Divider, Box, Chip, Stack, Button } from "@mui/material";
import VerifiedIcon from "@mui/icons-material/Verified";
import { useNavigate } from "react-router-dom";

const InvoiceShowActions = () => {
  const translate = useTranslate();
  const record = useRecordContext();
  const navigate = useNavigate();
  if (!record) return null;
  return (
    <TopToolbar>
      <Button
        startIcon={<VerifiedIcon />}
        variant="contained"
        size="small"
        onClick={() => navigate(`/invoices/${encodeURIComponent(record.source_file as string)}/verify`)}
      >
        {translate("aiflow.verification.verify")}
      </Button>
    </TopToolbar>
  );
};

export const InvoiceShow = () => {
  const translate = useTranslate();
  return (
    <Show title={translate("aiflow.invoices.detail")} actions={<InvoiceShowActions />}>
      <SimpleShowLayout>
        {/* Header */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.invoices.headerSection")}
        </Typography>
        <TextField source="source_file" label={translate("aiflow.invoices.file")} />
        <TextField source="header.invoice_number" label={translate("aiflow.invoices.invoiceNumber")} />
        <TextField source="header.invoice_type" label={translate("aiflow.invoices.type")} />
        <TextField source="header.invoice_date" label={translate("aiflow.invoices.date")} />
        <TextField source="header.fulfillment_date" label={translate("aiflow.invoices.fulfillmentDate")} />
        <TextField source="header.due_date" label={translate("aiflow.invoices.dueDate")} />
        <TextField source="header.payment_method" label={translate("aiflow.invoices.paymentMethod")} />
        <TextField source="header.currency" label={translate("aiflow.invoices.currency")} />

        <Divider sx={{ my: 2 }} />

        {/* Vendor */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.invoices.vendorSection")}
        </Typography>
        <TextField source="vendor.name" label={translate("aiflow.invoices.name")} />
        <TextField source="vendor.address" label={translate("aiflow.invoices.address")} />
        <TextField source="vendor.tax_number" label={translate("aiflow.invoices.taxNumber")} />

        <Divider sx={{ my: 2 }} />

        {/* Buyer */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.invoices.buyerSection")}
        </Typography>
        <TextField source="buyer.name" label={translate("aiflow.invoices.name")} />
        <TextField source="buyer.address" label={translate("aiflow.invoices.address")} />
        <TextField source="buyer.tax_number" label={translate("aiflow.invoices.taxNumber")} />

        <Divider sx={{ my: 2 }} />

        {/* Line items */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.invoices.lineItems")}
        </Typography>
        <ArrayField source="line_items">
          <Datagrid bulkActionButtons={false}>
            <NumberField source="line_number" label="#" />
            <TextField source="description" label={translate("aiflow.invoices.description")} />
            <NumberField source="quantity" label={translate("aiflow.invoices.quantity")} />
            <TextField source="unit" label={translate("aiflow.invoices.unit")} />
            <NumberField source="unit_price" label={translate("aiflow.invoices.unitPrice")} />
            <NumberField source="net_amount" label={translate("aiflow.invoices.netAmount")} />
            <TextField source="vat_rate" label={translate("aiflow.invoices.vatRate")} />
            <NumberField source="gross_amount" label={translate("aiflow.invoices.grossAmount")} />
          </Datagrid>
        </ArrayField>

        <Divider sx={{ my: 2 }} />

        {/* Totals */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.invoices.totalsSection")}
        </Typography>
        <NumberField source="totals.net_total" label={translate("aiflow.invoices.netTotal")} />
        <NumberField source="totals.vat_total" label={translate("aiflow.invoices.vatTotal")} />
        <NumberField source="totals.gross_total" label={translate("aiflow.invoices.grossTotal")} />

        <Divider sx={{ my: 2 }} />

        {/* Validation */}
        <Typography variant="h6" gutterBottom>
          {translate("aiflow.invoices.validationSection")}
        </Typography>
        <FunctionField
          label={translate("aiflow.invoices.valid")}
          render={(record: { validation?: { is_valid: boolean } }) => (
            <Chip
              label={record.validation?.is_valid ? "Valid" : "Invalid"}
              color={record.validation?.is_valid ? "success" : "error"}
              size="small"
            />
          )}
        />
        <NumberField source="validation.confidence_score" label={translate("aiflow.invoices.confidence")} />
        <FunctionField
          label={translate("aiflow.invoices.errors")}
          render={(record: { validation?: { errors?: string[] } }) => {
            const errors = record.validation?.errors || [];
            return errors.length > 0 ? (
              <Stack direction="column" spacing={0.5}>
                {errors.map((e, i) => (
                  <Typography key={i} variant="body2" color="error">{e}</Typography>
                ))}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">-</Typography>
            );
          }}
        />
        <TextField source="parser_used" label={translate("aiflow.invoices.parser")} />
      </SimpleShowLayout>
    </Show>
  );
};
