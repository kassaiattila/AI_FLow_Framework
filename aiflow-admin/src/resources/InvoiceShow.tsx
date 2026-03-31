import { Show, useTranslate, useRecordContext } from "react-admin";
import {
  Typography, Box, Chip, Stack, Button, Paper,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import VerifiedIcon from "@mui/icons-material/Verified";
import { useNavigate } from "react-router-dom";

// Compact label-value pair
const F = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.2, fontSize: "0.7rem" }}>
      {label}
    </Typography>
    <Typography variant="body2" sx={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
      {children || "–"}
    </Typography>
  </Box>
);

// Section card wrapper
const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
  <Paper variant="outlined" sx={{ p: 2 }}>
    <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5, fontSize: "0.85rem" }}>
      {title}
    </Typography>
    {children}
  </Paper>
);

const InvoiceShowContent = () => {
  const translate = useTranslate();
  const navigate = useNavigate();
  const record = useRecordContext();
  if (!record) return null;

  const vendor = (record.vendor || {}) as Record<string, unknown>;
  const buyer = (record.buyer || {}) as Record<string, unknown>;
  const header = (record.header || {}) as Record<string, unknown>;
  const totals = (record.totals || {}) as Record<string, unknown>;
  const validation = (record.validation || {}) as Record<string, unknown>;
  const lineItems = (record.line_items || []) as Array<Record<string, unknown>>;
  const errors = (validation.errors || []) as string[];

  const fmtNum = (v: unknown) => v != null ? Number(v).toLocaleString("hu-HU") : "–";

  return (
    <Box sx={{ p: 2, maxWidth: 1200, mx: "auto" }}>
      {/* Top bar: back + filename + verify */}
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/invoices")} size="small">
          {translate("ra.action.back")}
        </Button>
        <Typography variant="h6" sx={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {record.source_file as string}
        </Typography>
        <Chip
          label={validation.is_valid ? "Valid" : "Invalid"}
          color={validation.is_valid ? "success" : "error"}
          size="small"
        />
        <Button
          startIcon={<VerifiedIcon />}
          variant="contained"
          size="small"
          onClick={() => navigate(`/invoices/${encodeURIComponent(record.source_file as string)}/verify`)}
        >
          {translate("aiflow.verification.verify")}
        </Button>
      </Stack>

      {/* Main grid: 3 columns */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" }, gap: 2, mb: 2 }}>

        {/* Invoice header */}
        <Section title={translate("aiflow.invoices.headerSection")}>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1.5 }}>
            <F label={translate("aiflow.invoices.invoiceNumber")}>{header.invoice_number as string}</F>
            <F label={translate("aiflow.invoices.type")}>{header.invoice_type as string}</F>
            <F label={translate("aiflow.invoices.date")}>{header.invoice_date as string}</F>
            <F label={translate("aiflow.invoices.fulfillmentDate")}>{header.fulfillment_date as string}</F>
            <F label={translate("aiflow.invoices.dueDate")}>{header.due_date as string}</F>
            <F label={translate("aiflow.invoices.paymentMethod")}>{header.payment_method as string}</F>
            <F label={translate("aiflow.invoices.currency")}>{header.currency as string}</F>
          </Box>
        </Section>

        {/* Vendor */}
        <Section title={translate("aiflow.invoices.vendorSection")}>
          <Stack spacing={1.5}>
            <F label={translate("aiflow.invoices.name")}>{vendor.name as string}</F>
            <F label={translate("aiflow.invoices.address")}>{vendor.address as string}</F>
            <F label={translate("aiflow.invoices.taxNumber")}>{vendor.tax_number as string}</F>
          </Stack>
        </Section>

        {/* Buyer */}
        <Section title={translate("aiflow.invoices.buyerSection")}>
          <Stack spacing={1.5}>
            <F label={translate("aiflow.invoices.name")}>{buyer.name as string}</F>
            <F label={translate("aiflow.invoices.address")}>{buyer.address as string}</F>
            <F label={translate("aiflow.invoices.taxNumber")}>{buyer.tax_number as string}</F>
          </Stack>
        </Section>
      </Box>

      {/* Line items table — full width */}
      <Paper variant="outlined" sx={{ mb: 2 }}>
        <Box sx={{ px: 2, pt: 1.5, pb: 0.5 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, fontSize: "0.85rem" }}>
            {translate("aiflow.invoices.lineItems")}
          </Typography>
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>#</TableCell>
                <TableCell>{translate("aiflow.invoices.description")}</TableCell>
                <TableCell align="right">{translate("aiflow.invoices.quantity")}</TableCell>
                <TableCell>{translate("aiflow.invoices.unit")}</TableCell>
                <TableCell align="right">{translate("aiflow.invoices.unitPrice")}</TableCell>
                <TableCell align="right">{translate("aiflow.invoices.netAmount")}</TableCell>
                <TableCell align="right">{translate("aiflow.invoices.vatRate")}</TableCell>
                <TableCell align="right">{translate("aiflow.invoices.grossAmount")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lineItems.map((item, i) => (
                <TableRow key={i}>
                  <TableCell>{(item.line_number as number) || i + 1}</TableCell>
                  <TableCell>{item.description as string}</TableCell>
                  <TableCell align="right">{fmtNum(item.quantity)}</TableCell>
                  <TableCell>{(item.unit as string) || "–"}</TableCell>
                  <TableCell align="right">{fmtNum(item.unit_price)}</TableCell>
                  <TableCell align="right">{fmtNum(item.net_amount)}</TableCell>
                  <TableCell align="right">{(item.vat_rate as string) || "0"}</TableCell>
                  <TableCell align="right">{fmtNum(item.gross_amount)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Bottom row: Totals + Validation side by side */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>

        {/* Totals */}
        <Section title={translate("aiflow.invoices.totalsSection")}>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1.5 }}>
            <F label={translate("aiflow.invoices.netTotal")}>{fmtNum(totals.net_total)}</F>
            <F label={translate("aiflow.invoices.vatTotal")}>{fmtNum(totals.vat_total)}</F>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.2, fontSize: "0.7rem" }}>
                {translate("aiflow.invoices.grossTotal")}
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {fmtNum(totals.gross_total)} {header.currency as string}
              </Typography>
            </Box>
          </Box>
        </Section>

        {/* Validation */}
        <Section title={translate("aiflow.invoices.validationSection")}>
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1.5 }}>
            <F label={translate("aiflow.invoices.valid")}>
              <Chip
                label={validation.is_valid ? "Valid" : "Invalid"}
                color={validation.is_valid ? "success" : "error"}
                size="small"
              />
            </F>
            <F label={translate("aiflow.invoices.confidence")}>
              {validation.confidence_score != null ? `${((validation.confidence_score as number) * 100).toFixed(0)}%` : "–"}
            </F>
            <F label={translate("aiflow.invoices.parser")}>{record.parser_used as string}</F>
          </Box>
          {errors.length > 0 && (
            <Box sx={{ mt: 1.5 }}>
              <Typography variant="caption" color="error" sx={{ fontWeight: 600 }}>
                {translate("aiflow.invoices.errors")}:
              </Typography>
              {errors.map((e, i) => (
                <Typography key={i} variant="body2" color="error" sx={{ fontSize: "0.8rem" }}>• {e}</Typography>
              ))}
            </Box>
          )}
        </Section>
      </Box>
    </Box>
  );
};

export const InvoiceShow = () => {
  const translate = useTranslate();
  return (
    <Show title={translate("aiflow.invoices.detail")} actions={false}>
      <InvoiceShowContent />
    </Show>
  );
};
