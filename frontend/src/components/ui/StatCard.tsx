interface TrendProps {
  label: string;
  positive: boolean;
}

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  iconBg?: string;
  iconColor?: string;
  trend?: TrendProps;
}

export function StatCard({
  label,
  value,
  icon,
  iconBg = "bg-gray-100 dark:bg-slate-700",
  iconColor = "text-gray-600 dark:text-slate-300",
  trend,
}: StatCardProps) {
  const formatted = typeof value === "number" ? value.toLocaleString() : value;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm p-5">
      <div className="flex items-center justify-between mb-3">
        <span className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${iconBg} ${iconColor}`}>
          {icon}
        </span>
        {trend && (
          <span
            className={`text-xs font-medium ${trend.positive ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
            aria-label={`Trend: ${trend.positive ? "up" : "down"} ${trend.label}`}
          >
            {trend.positive ? "↑" : "↓"} {trend.label}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-slate-100 mb-0.5">{formatted}</p>
      <p className="text-sm text-gray-500 dark:text-slate-400">{label}</p>
    </div>
  );
}
