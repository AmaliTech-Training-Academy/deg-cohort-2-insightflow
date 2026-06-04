import { apiFetch } from "./client";
import type { DashboardStats } from "@/types";
import type { OnlineOrdersJob } from "./onlineOrders";

interface OnlineOrdersJobsPage {
  count: number;
  results: OnlineOrdersJob[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const jobs = await apiFetch<OnlineOrdersJobsPage>(
    "/ingestion/online-orders/jobs/?page=1"
  );

  const todayStr = new Date().toDateString();
  const todayJobs = jobs.results.filter(
    (j) => new Date(j.created_at).toDateString() === todayStr
  );

  const jobsToday = todayJobs.length;
  const jobsSuccessToday = todayJobs.filter((j) => j.status === "completed").length;
  const jobsFailedToday = todayJobs.filter((j) => j.status === "failed").length;
  const recordsIngested = jobs.results
    .filter((j) => j.status === "completed")
    .reduce((sum, j) => sum + (j.valid_orders ?? 0), 0);

  // Derive online orders source health from most recent job
  const latest = jobs.results[0];
  const onlineStatus =
    !latest ? "degraded"
    : latest.status === "completed" ? "healthy"
    : latest.status === "failed" ? "down"
    : "degraded";

  return {
    jobsToday,
    jobsSuccessToday,
    jobsFailedToday,
    recordsIngested,
    sources: [
      {
        id: "1",
        name: "POS System",
        type: "pos",
        lastSyncAt: null,
        status: "degraded",
      },
      {
        id: "2",
        name: "Online Orders",
        type: "online_orders",
        lastSyncAt: latest?.updated_at ?? null,
        status: onlineStatus,
      },
      {
        id: "3",
        name: "Inventory",
        type: "inventory",
        lastSyncAt: null,
        status: "degraded",
      },
      {
        id: "4",
        name: "Customer Feedback",
        type: "feedback",
        lastSyncAt: null,
        status: "degraded",
      },
    ],
  };
}
