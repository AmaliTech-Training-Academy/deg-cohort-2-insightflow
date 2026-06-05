type Status = "pending" | "processing" | "completed" | "failed" | "healthy" | "degraded" | "down";

const colorMap: Record<Status, string> = {
  pending:    "bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:ring-yellow-700/50",
  processing: "bg-blue-50 text-blue-700 ring-1 ring-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:ring-blue-700/50",
  completed:  "bg-green-50 text-green-700 ring-1 ring-green-200 dark:bg-green-900/30 dark:text-green-300 dark:ring-green-700/50",
  failed:     "bg-red-50 text-red-700 ring-1 ring-red-200 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-700/50",
  healthy:    "bg-green-50 text-green-700 ring-1 ring-green-200 dark:bg-green-900/30 dark:text-green-300 dark:ring-green-700/50",
  degraded:   "bg-yellow-50 text-yellow-700 ring-1 ring-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-300 dark:ring-yellow-700/50",
  down:       "bg-red-50 text-red-700 ring-1 ring-red-200 dark:bg-red-900/30 dark:text-red-300 dark:ring-red-700/50",
};

const dotMap: Record<Status, string> = {
  pending:    "bg-yellow-500",
  processing: "bg-blue-500",
  completed:  "bg-green-500",
  failed:     "bg-red-500",
  healthy:    "bg-green-500",
  degraded:   "bg-yellow-500",
  down:       "bg-red-500",
};

interface StatusBadgeProps {
  status: Status;
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${colorMap[status]}`}>
      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotMap[status]}`} aria-hidden="true" />
      {label ?? status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
