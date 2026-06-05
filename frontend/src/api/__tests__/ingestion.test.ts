import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  triggerOnlineOrders,
  getOnlineOrdersJobs,
  getOnlineOrdersJobStatus,
  toIngestionJob,
} from "@/api/onlineOrders";
import { getIngestionHistory } from "@/api/history";
import { getDashboardStats } from "@/api/dashboard";

vi.mock("@/api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/tokenStorage", () => ({ getToken: vi.fn(() => "test-token") }));

async function getApiFetch() {
  const { apiFetch } = await import("@/api/client");
  return vi.mocked(apiFetch);
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const mockOnlineJob = {
  id: 1,
  status: "completed",
  trigger: "manual" as const,
  total_orders: 500,
  valid_orders: 490,
  error_orders: 10,
  pages_fetched: 5,
  error_report: {},
  created_at: "2026-06-04T10:00:00Z",
  updated_at: "2026-06-04T10:01:30Z",
};

const mockPagedJobs = {
  count: 1,
  next: null,
  previous: null,
  results: [mockOnlineJob],
};

// ── toIngestionJob ─────────────────────────────────────────────────────────────

describe("toIngestionJob", () => {
  it("maps id, sourceType, status correctly", () => {
    const job = toIngestionJob(mockOnlineJob);
    expect(job.id).toBe("1");
    expect(job.sourceType).toBe("online_orders");
    expect(job.status).toBe("completed");
  });

  it('maps backend "running" to frontend "processing"', () => {
    const job = toIngestionJob({ ...mockOnlineJob, status: "running" });
    expect(job.status).toBe("processing");
  });

  it("maps recordsTotal and recordsProcessed from orders fields", () => {
    const job = toIngestionJob(mockOnlineJob);
    expect(job.recordsTotal).toBe(500);
    expect(job.recordsProcessed).toBe(490);
  });

  it("sets errorMessage when error_orders > 0", () => {
    const job = toIngestionJob(mockOnlineJob);
    expect(job.errorMessage).toBe("10 orders failed");
  });

  it("errorMessage is null when error_orders is 0", () => {
    const job = toIngestionJob({ ...mockOnlineJob, error_orders: 0 });
    expect(job.errorMessage).toBeNull();
  });

  it("sets errorMessage when status is failed regardless of error_orders", () => {
    const job = toIngestionJob({
      ...mockOnlineJob,
      status: "failed",
      error_orders: 0,
    });
    expect(job.errorMessage).not.toBeNull();
  });

  it("sets null recordsTotal when total_orders is null", () => {
    const job = toIngestionJob({ ...mockOnlineJob, total_orders: null });
    expect(job.recordsTotal).toBeNull();
  });
});

// ── triggerOnlineOrders ───────────────────────────────────────────────────────

describe("triggerOnlineOrders", () => {
  beforeEach(() => vi.clearAllMocks());

  it("POSTs to /ingestion/online-orders/trigger/", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ ...mockOnlineJob, status: "pending", id: 2 });

    const result = await triggerOnlineOrders();

    expect(apiFetch).toHaveBeenCalledWith(
      "/ingestion/online-orders/trigger/",
      expect.objectContaining({ method: "POST" })
    );
    expect(result.status).toBe("pending");
    expect(result.id).toBe(2);
  });
});

// ── getOnlineOrdersJobs ───────────────────────────────────────────────────────

describe("getOnlineOrdersJobs", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches page 1 by default", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockPagedJobs);

    await getOnlineOrdersJobs();

    expect(apiFetch).toHaveBeenCalledWith(
      "/ingestion/online-orders/jobs/?page=1"
    );
  });

  it("fetches the requested page number", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockPagedJobs);

    await getOnlineOrdersJobs(3);

    expect(apiFetch).toHaveBeenCalledWith(
      "/ingestion/online-orders/jobs/?page=3"
    );
  });

  it("returns mapped IngestionJob results", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockPagedJobs);

    const result = await getOnlineOrdersJobs();

    expect(result.count).toBe(1);
    expect(result.results).toHaveLength(1);
    expect(result.results[0].sourceType).toBe("online_orders");
    expect(result.results[0].status).toBe("completed");
  });

  it("preserves pagination metadata", async () => {
    const apiFetch = await getApiFetch();
    const nextUrl = "http://localhost/api/ingestion/online-orders/jobs/?page=2";
    apiFetch.mockResolvedValue({ ...mockPagedJobs, count: 42, next: nextUrl });

    const result = await getOnlineOrdersJobs();

    expect(result.count).toBe(42);
    expect(result.next).toBe(nextUrl);
  });
});

// ── getOnlineOrdersJobStatus ──────────────────────────────────────────────────

describe("getOnlineOrdersJobStatus", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches the correct job status URL", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockOnlineJob);

    await getOnlineOrdersJobStatus(1);

    expect(apiFetch).toHaveBeenCalledWith(
      "/ingestion/online-orders/1/status/"
    );
  });

  it("returns a mapped IngestionJob", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockOnlineJob);

    const result = await getOnlineOrdersJobStatus(1);

    expect(result.id).toBe("1");
    expect(result.recordsTotal).toBe(500);
    expect(result.recordsProcessed).toBe(490);
  });
});

// ── getIngestionHistory ───────────────────────────────────────────────────────

describe("getIngestionHistory", () => {
  beforeEach(() => vi.clearAllMocks());

  it("delegates to getOnlineOrdersJobs with the given page", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockPagedJobs);

    const result = await getIngestionHistory(2);

    expect(apiFetch).toHaveBeenCalledWith(
      "/ingestion/online-orders/jobs/?page=2"
    );
    expect(result.results).toHaveLength(1);
  });
});

// ── getDashboardStats ─────────────────────────────────────────────────────────

describe("getDashboardStats", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns zero job counts when no jobs exist", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ count: 0, results: [] });

    const stats = await getDashboardStats();

    expect(stats.jobsToday).toBe(0);
    expect(stats.jobsSuccessToday).toBe(0);
    expect(stats.jobsFailedToday).toBe(0);
    expect(stats.recordsIngested).toBe(0);
  });

  it("counts only today's jobs for jobsToday", async () => {
    const apiFetch = await getApiFetch();
    const oldJob = {
      ...mockOnlineJob,
      created_at: "2020-01-01T10:00:00Z",
      status: "completed",
    };
    apiFetch.mockResolvedValue({
      count: 2,
      results: [mockOnlineJob, oldJob],
    });

    const stats = await getDashboardStats();

    // Only the job with today's date should count
    expect(stats.jobsToday).toBeLessThanOrEqual(1);
  });

  it("sums valid_orders from completed jobs for recordsIngested", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      count: 2,
      results: [
        { ...mockOnlineJob, valid_orders: 100, status: "completed" },
        { ...mockOnlineJob, id: 2, valid_orders: 200, status: "completed" },
      ],
    });

    const stats = await getDashboardStats();

    expect(stats.recordsIngested).toBe(300);
  });

  it("does not count failed jobs in recordsIngested", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      count: 1,
      results: [{ ...mockOnlineJob, status: "failed", valid_orders: 50 }],
    });

    const stats = await getDashboardStats();

    expect(stats.recordsIngested).toBe(0);
  });

  it('sets online orders source to "healthy" when latest job completed', async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      count: 1,
      results: [{ ...mockOnlineJob, status: "completed" }],
    });

    const stats = await getDashboardStats();
    const onlineSource = stats.sources.find((s) => s.type === "online_orders");

    expect(onlineSource?.status).toBe("healthy");
  });

  it('sets online orders source to "down" when latest job failed', async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      count: 1,
      results: [{ ...mockOnlineJob, status: "failed" }],
    });

    const stats = await getDashboardStats();
    const onlineSource = stats.sources.find((s) => s.type === "online_orders");

    expect(onlineSource?.status).toBe("down");
  });

  it('sets online orders source to "degraded" when no jobs exist', async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ count: 0, results: [] });

    const stats = await getDashboardStats();
    const onlineSource = stats.sources.find((s) => s.type === "online_orders");

    expect(onlineSource?.status).toBe("degraded");
  });

  it("returns all four data sources", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ count: 0, results: [] });

    const stats = await getDashboardStats();

    expect(stats.sources).toHaveLength(4);
    const types = stats.sources.map((s) => s.type);
    expect(types).toContain("pos");
    expect(types).toContain("online_orders");
    expect(types).toContain("inventory");
    expect(types).toContain("feedback");
  });
});
