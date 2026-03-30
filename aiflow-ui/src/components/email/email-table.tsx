"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { EmailProcessingResult } from "@/lib/types";
import { PriorityBadge, IntentBadge, MethodBadge, formatDate } from "./shared";

interface EmailTableProps {
  emails: EmailProcessingResult[];
  selectedId: string | null;
  onSelect: (email: EmailProcessingResult) => void;
}

export function EmailTable({ emails, selectedId, onSelect }: EmailTableProps) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[180px]">Feladó</TableHead>
            <TableHead>Tárgy</TableHead>
            <TableHead className="w-[120px]">Intent</TableHead>
            <TableHead className="w-[80px]">Módszer</TableHead>
            <TableHead className="w-[90px]">Prioritás</TableHead>
            <TableHead className="w-[60px]">Csatol.</TableHead>
            <TableHead className="w-[130px]">Dátum</TableHead>
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
                Nincs feldolgozott email
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
