"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useI18n } from "@/hooks/use-i18n";
import type { EmailProcessingResult } from "@/lib/types";
import { PriorityBadge, IntentBadge, MethodBadge, formatDate } from "./shared";

interface EmailTableProps {
  emails: EmailProcessingResult[];
  selectedId: string | null;
  onSelect: (email: EmailProcessingResult) => void;
}

export function EmailTable({ emails, selectedId, onSelect }: EmailTableProps) {
  const { t } = useI18n();
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[180px]">{t("table.sender")}</TableHead>
            <TableHead>{t("table.subject")}</TableHead>
            <TableHead className="w-[120px]">{t("table.intent")}</TableHead>
            <TableHead className="w-[80px]">{t("table.method")}</TableHead>
            <TableHead className="w-[90px]">{t("table.priority")}</TableHead>
            <TableHead className="w-[60px]">{t("table.attachments")}</TableHead>
            <TableHead className="w-[130px]">{t("common.date")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {emails.map((email) => (
            <TableRow
              key={email.email_id}
              className={`cursor-pointer ${
                selectedId === email.email_id ? "bg-muted" : "hover:bg-muted/50"
              }`}
              onClick={() => onSelect(email)}
            >
              <TableCell className="text-sm font-medium truncate max-w-[180px]">
                {email.sender}
              </TableCell>
              <TableCell className="text-sm truncate max-w-[300px]">{email.subject}</TableCell>
              <TableCell>
                {email.intent && (
                  <IntentBadge
                    intent={email.intent.intent_display_name}
                    confidence={email.intent.confidence}
                  />
                )}
              </TableCell>
              <TableCell>
                {email.intent && <MethodBadge method={email.intent.method} />}
              </TableCell>
              <TableCell>
                {email.priority && <PriorityBadge level={email.priority.priority_level} />}
              </TableCell>
              <TableCell className="text-center text-sm">
                {email.attachment_count > 0 ? email.attachment_count : "-"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {formatDate(email.received_date)}
              </TableCell>
            </TableRow>
          ))}
          {emails.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                {t("email.noEmails")}
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
