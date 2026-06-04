import type { ReactNode } from "react";

interface TrendProps {
  label: string;
  positive: boolean;
}

interface StatCardProps {
  label: string;
  value: string | number;
  icon: ReactNode;
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
    <div className="rounded-lg border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm px-5 pt-5 pb-4">
      <div className="flex items-start justify-between mb-4">
        <span
          className={`inline-flex items-center justify-center w-10 h-10 rounded-lg shrink-0 ${iconBg} ${iconColor}`}
        >
          {icon}
        </span>
        {trend && (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium tabular-nums ${
              trend.positive
                ? "bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-400"
                : "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-400"
            }`}
            aria-label={`Trend: ${trend.positive ? "up" : "down"} ${trend.label}`}
          >
            {trend.positive ? "↑" : "↓"} {trend.label}
          </span>
        )}
      </div>
      <p className="text-3xl font-bold text-gray-900 dark:text-slate-100 tabular-nums leading-none mb-1">
        {formatted}
      </p>
      <p className="text-sm text-gray-500 dark:text-slate-400">{label}</p>
    </div>
  );
}
