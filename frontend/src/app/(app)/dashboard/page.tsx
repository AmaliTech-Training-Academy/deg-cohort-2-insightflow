"use client";

import { useQuery } from "@tanstack/react-query";
import { getDashboardStats } from "@/api/dashboard";
import { StatCard } from "@/components/ui/StatCard";
import { SourceHealthTable } from "@/components/dashboard/SourceHealthTable";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { AlertBanner } from "@/components/ui/AlertBanner";

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return (
      <div aria-label="Loading dashboard">
        <div className="mb-6">
          <div className="h-8 w-40 rounded bg-gray-200 animate-pulse mb-2" />
          <div className="h-4 w-64 rounded bg-gray-200 animate-pulse" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-gray-200 bg-white shadow-sm p-5 h-28 animate-pulse bg-gray-100" />
          ))}
        </div>
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <AlertBanner
        variant="error"
        message="Failed to load dashboard stats. Please refresh the page."
      />
    );
  }

  const successRate =
    data.jobsToday > 0
      ? Math.round((data.jobsSuccessToday / data.jobsToday) * 100)
      : 0;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-slate-100">Dashboard</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          Operational overview of your data pipeline. Auto-refreshes every 30s.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Jobs Today"
          value={data.jobsToday}
          icon={<BriefcaseIcon />}
          iconBg="bg-blue-50 dark:bg-blue-950/40"
          iconColor="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          label="Successful"
          value={data.jobsSuccessToday}
          icon={<CheckIcon />}
          iconBg="bg-green-50 dark:bg-green-950/40"
          iconColor="text-green-600 dark:text-green-400"
          trend={
            data.jobsToday > 0
              ? { label: `${successRate}% success rate`, positive: successRate >= 80 }
              : undefined
          }
        />
        <StatCard
          label="Failed"
          value={data.jobsFailedToday}
          icon={<XCircleIcon />}
          iconBg="bg-red-50 dark:bg-red-950/40"
          iconColor="text-red-600 dark:text-red-400"
          trend={
            data.jobsFailedToday > 0
              ? { label: `${data.jobsFailedToday} need review`, positive: false }
              : undefined
          }
        />
        <StatCard
          label="Records Ingested"
          value={data.recordsIngested}
          icon={<DatabaseIcon />}
          iconBg="bg-purple-50 dark:bg-purple-950/40"
          iconColor="text-purple-600 dark:text-purple-400"
        />
      </div>

      <SourceHealthTable sources={data.sources} />
    </div>
  );
}

function BriefcaseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function XCircleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  );
}
