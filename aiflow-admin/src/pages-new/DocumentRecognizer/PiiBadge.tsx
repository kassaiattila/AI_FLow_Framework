/**
 * PII level badge — Sprint V SV-4.
 * Color tokens use Tailwind v4 utility classes.
 */

import type { PiiLevel } from "./types";

const STYLES: Record<PiiLevel, string> = {
  low: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  high: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
};

export function PiiBadge({ level }: { level: PiiLevel }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[level]}`}
      data-testid={`pii-badge-${level}`}
    >
      PII {level}
    </span>
  );
}
