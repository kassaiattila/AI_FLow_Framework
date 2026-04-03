/** Floating scroll-to-bottom button. */

export function ScrollToBottom({ visible, onClick }: { visible: boolean; onClick: () => void }) {
  if (!visible) return null;

  return (
    <button
      onClick={onClick}
      className="absolute bottom-20 left-1/2 z-10 -translate-x-1/2 rounded-full border border-gray-200 bg-white p-2 shadow-lg transition-all hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700"
      aria-label="Scroll to bottom"
    >
      <svg className="h-4 w-4 text-gray-600 dark:text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    </button>
  );
}
