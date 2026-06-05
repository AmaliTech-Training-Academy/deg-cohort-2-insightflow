import { apiFetch } from "./client";
import type { DashboardStats } from "@/types";
import type { OnlineOrdersJob } from "./onlineOrders";

interface PosJobResponse {
  id: number;
  file_name: string;
  status: string;
  total_rows: number | null;
  valid_rows: number;
  rejected_rows: number;
  error_rows: number;
  error_report: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

interface Page<T> {
  count: number;
  results: T[];
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const [posData, ooData] = await Promise.all([
    apiFetch<Page<PosJobResponse>>("/ingestion/pos/jobs/?page=1"),
    apiFetch<Page<OnlineOrdersJob>>("/ingestion/online-orders/jobs/?page=1"),
  ]);

  const todayStr = new Date().toDateString();

  const posToday = posData.results.filter(
    (j) => new Date(j.created_at).toDateString() === todayStr
  );
  const ooToday = ooData.results.filter(
    (j) => new Date(j.created_at).toDateString() === todayStr
  );

  const jobsToday = posToday.length + ooToday.length;
  const jobsSuccessToday =
    posToday.filter((j) => j.status === "completed").length +
    ooToday.filter((j) => j.status === "completed").length;
  const jobsFailedToday =
    posToday.filter((j) => j.status === "failed").length +
    ooToday.filter((j) => j.status === "failed").length;

  const recordsIngested =
    posData.results
      .filter((j) => j.status === "completed")
      .reduce((sum, j) => sum + j.valid_rows, 0) +
    ooData.results
      .filter((j) => j.status === "completed")
      .reduce((sum, j) => sum + (j.valid_orders ?? 0), 0);

  const latestPos = posData.results[0];
  const latestOo = ooData.results[0];

  function jobStatus(job: { status: string } | undefined): "healthy" | "degraded" | "down" {
    if (!job) return "degraded";
    if (job.status === "completed") return "healthy";
    if (job.status === "failed") return "down";
    return "degraded";
  }

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
        lastSyncAt: latestPos?.updated_at ?? null,
        status: jobStatus(latestPos),
      },
      {
        id: "2",
        name: "Online Orders",
        type: "online_orders",
        lastSyncAt: latestOo?.updated_at ?? null,
        status: jobStatus(latestOo),
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
