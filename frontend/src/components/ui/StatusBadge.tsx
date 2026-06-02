type Status = "pending" | "processing" | "completed" | "failed" | "healthy" | "degraded" | "down";

const colorMap: Record<Status, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  processing: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  healthy: "bg-green-100 text-green-800",
  degraded: "bg-yellow-100 text-yellow-800",
  down: "bg-red-100 text-red-800",
};

interface StatusBadgeProps {
  status: Status;
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorMap[status]}`}
    >
      {label ?? status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
