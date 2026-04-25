/**
 * LoadingState — skeleton/spinner loading indicator.
 * Use instead of MUI CircularProgress.
 */

interface LoadingStateProps {
  /** Full page centered or inline */
  fullPage?: boolean;
  /** Number of skeleton rows to show */
  rows?: number;
}

export function LoadingState({
  fullPage = false,
  rows = 3,
}: LoadingStateProps) {
  if (fullPage) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-500" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="animate-pulse">
          <div
            className="h-4 rounded bg-gray-200 dark:bg-gray-700"
            style={{ width: `${85 - i * 15}%` }}
          />
        </div>
      ))}
    </div>
  );
}
