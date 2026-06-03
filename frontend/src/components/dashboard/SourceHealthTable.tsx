import type { DataSource } from "@/types";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";

const SOURCE_LABELS: Record<string, string> = {
  pos:           "POS",
  inventory:     "Inventory",
  online_orders: "Online Orders",
  feedback:      "Feedback",
};

function relativeTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

interface SourceHealthTableProps {
  sources: DataSource[];
}

export function SourceHealthTable({ sources }: SourceHealthTableProps) {
  return (
    <Card title="Data Source Health">
      <div className="overflow-x-auto -mx-5 -mb-5">
        <table className="min-w-full divide-y divide-gray-100 dark:divide-slate-700 text-sm">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>
              {["Source", "Type", "Last Sync", "Status"].map((h) => (
                <th
                  key={h}
                  className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-slate-400"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700 bg-white dark:bg-slate-800">
            {sources.map((src) => (
              <tr key={src.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors">
                <td className="px-5 py-3 font-medium text-gray-900 dark:text-slate-100">
                  {src.name}
                </td>
                <td className="px-5 py-3 text-gray-500 dark:text-slate-400">
                  {SOURCE_LABELS[src.type] ?? src.type}
                </td>
                <td className="px-5 py-3 text-gray-500 dark:text-slate-400">
                  {relativeTime(src.lastSyncAt)}
                </td>
                <td className="px-5 py-3">
                  <StatusBadge status={src.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
