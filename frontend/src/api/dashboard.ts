// Real calls: import { apiFetch } from "./client";
// Base path: /api/ingestion/
import type { DashboardStats } from "@/types";

export async function getDashboardStats(): Promise<DashboardStats> {
  // GET /api/ingestion/dashboard/
  return {
    jobsToday: 12,
    jobsSuccessToday: 10,
    jobsFailedToday: 2,
    recordsIngested: 48320,
    sources: [
      {
        id: "1",
        name: "POS System",
        type: "pos",
        lastSyncAt: new Date().toISOString(),
        status: "healthy",
      },
      {
        id: "2",
        name: "Online Orders",
        type: "online_orders",
        lastSyncAt: new Date().toISOString(),
        status: "healthy",
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
        lastSyncAt: new Date(Date.now() - 86400000).toISOString(),
        status: "healthy",
      },
    ],
  };
}
