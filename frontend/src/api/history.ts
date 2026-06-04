import { getOnlineOrdersJobs } from "./onlineOrders";
import type { IngestionJob, PaginatedResponse } from "@/types";

export async function getIngestionHistory(
  page = 1
): Promise<PaginatedResponse<IngestionJob>> {
  // Only online orders jobs have a list endpoint on the backend.
  // POS job history requires a backend list endpoint not yet available.
  return getOnlineOrdersJobs(page);
}
