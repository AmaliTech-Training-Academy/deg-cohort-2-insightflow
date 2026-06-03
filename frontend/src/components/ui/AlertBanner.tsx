type AlertVariant = "info" | "success" | "warning" | "error";

const styles: Record<AlertVariant, string> = {
  info:    "bg-blue-50  dark:bg-blue-900/30  border-blue-200  dark:border-blue-700  text-blue-800  dark:text-blue-300",
  success: "bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-700 text-green-800 dark:text-green-300",
  warning: "bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-700 text-yellow-800 dark:text-yellow-300",
  error:   "bg-red-50   dark:bg-red-900/30   border-red-200   dark:border-red-700   text-red-800   dark:text-red-300",
};

interface AlertBannerProps {
  variant?: AlertVariant;
  message: string;
  onDismiss?: () => void;
}

export function AlertBanner({ variant = "info", message, onDismiss }: AlertBannerProps) {
  return (
    <div
      className={`flex items-start justify-between rounded-md border px-4 py-3 text-sm ${styles[variant]}`}
      role="alert"
    >
      <span>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="ml-4 shrink-0 opacity-70 hover:opacity-100 transition-opacity"
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}
