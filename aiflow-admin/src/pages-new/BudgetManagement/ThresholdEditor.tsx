/**
 * ThresholdEditor — chip input for per-tenant budget alert thresholds.
 * Sprint N / S123. Mirrors the backend validator in
 * ``TenantBudget._validate_thresholds`` (ints in [1, 100], deduped + sorted).
 */

import { useMemo, useState } from "react";
import type { KeyboardEvent, ChangeEvent } from "react";

interface ThresholdEditorProps {
  value: number[];
  onChange: (next: number[]) => void;
  disabled?: boolean;
  /** testid prefix for Playwright targeting */
  testid?: string;
}

function normalize(list: number[]): number[] {
  return Array.from(
    new Set(list.filter((n) => Number.isInteger(n) && n >= 1 && n <= 100)),
  ).sort((a, b) => a - b);
}

export function ThresholdEditor({
  value,
  onChange,
  disabled,
  testid = "threshold",
}: ThresholdEditorProps) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  const sorted = useMemo(() => normalize(value), [value]);

  const commitDraft = () => {
    const trimmed = draft.trim();
    if (!trimmed) {
      setError(null);
      return;
    }
    const parsed = Number(trimmed);
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 100) {
      setError(`Ervenytelen: csak 1..100 kozotti egesz szam.`);
      return;
    }
    if (sorted.includes(parsed)) {
      setError(`Mar van ${parsed}% kuszob.`);
      setDraft("");
      return;
    }
    onChange(normalize([...sorted, parsed]));
    setDraft("");
    setError(null);
  };

  const remove = (pct: number) => {
    onChange(normalize(sorted.filter((v) => v !== pct)));
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitDraft();
    } else if (
      event.key === "Backspace" &&
      draft.length === 0 &&
      sorted.length > 0
    ) {
      remove(sorted[sorted.length - 1]);
    }
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setDraft(event.target.value);
  };

  const descriptionId = `${testid}-help`;
  const errorId = `${testid}-error`;

  return (
    <div className="space-y-1" data-testid={testid}>
      <div
        className={`flex flex-wrap items-center gap-1.5 rounded-lg border px-2 py-1.5 text-sm transition-colors ${
          disabled
            ? "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800"
            : "border-gray-300 bg-white focus-within:border-brand-500 dark:border-gray-600 dark:bg-gray-900"
        }`}
      >
        {sorted.map((pct) => (
          <span
            key={pct}
            data-testid={`${testid}-chip-${pct}`}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700 ring-1 ring-brand-200 dark:bg-brand-900/30 dark:text-brand-300 dark:ring-brand-800"
          >
            {pct}%
            {!disabled && (
              <button
                type="button"
                aria-label={`Remove threshold ${pct}%`}
                data-testid={`${testid}-remove-${pct}`}
                onClick={() => remove(pct)}
                className="rounded-full p-0.5 text-brand-500 hover:bg-brand-100 hover:text-brand-700 dark:hover:bg-brand-800"
              >
                <svg
                  className="h-3 w-3"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            )}
          </span>
        ))}
        <input
          type="text"
          inputMode="numeric"
          value={draft}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onBlur={commitDraft}
          disabled={disabled}
          placeholder={sorted.length === 0 ? "pl: 50, 80, 95" : ""}
          aria-describedby={error ? errorId : descriptionId}
          aria-invalid={error ? true : undefined}
          data-testid={`${testid}-input`}
          className="min-w-[4rem] flex-1 border-0 bg-transparent p-0 text-sm text-gray-900 outline-none placeholder:text-gray-400 disabled:cursor-not-allowed dark:text-gray-100"
        />
      </div>
      {error ? (
        <p
          id={errorId}
          role="alert"
          className="text-xs text-red-600 dark:text-red-400"
        >
          {error}
        </p>
      ) : (
        <p
          id={descriptionId}
          className="text-xs text-gray-500 dark:text-gray-400"
        >
          Enter / vesszo = hozzaadas. Backspace = utolso torles.
        </p>
      )}
    </div>
  );
}
