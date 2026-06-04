import { describe, it, expect, vi, beforeEach } from "vitest";
import { uploadFile, getJobStatus } from "@/api/uploads";

vi.mock("@/api/client", () => ({ apiFetch: vi.fn() }));
vi.mock("@/lib/tokenStorage", () => ({ getToken: vi.fn(() => "test-token") }));

async function getApiFetch() {
  const { apiFetch } = await import("@/api/client");
  return vi.mocked(apiFetch);
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const mockStatusResponse = {
  job_id: 1,
  status: "completed",
  total_rows: 3036,
  valid_rows: 3001,
  rejected_rows: 25,
  error_rows: 10,
  created_at: "2026-06-04T10:00:00Z",
  updated_at: "2026-06-04T10:01:30Z",
};

// ── uploadFile ────────────────────────────────────────────────────────────────

describe("uploadFile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("POSTs to /ingestion/pos/ with FormData", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        job_id: 1,
        status: "pending",
        total_rows: 3036,
        message: "File accepted.",
      }),
    } as Response);

    const file = new File(["a,b\n1,2"], "test.csv", { type: "text/csv" });
    await uploadFile(file, "pos");

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/ingestion/pos/");
    expect((options as RequestInit).method).toBe("POST");
    expect((options as RequestInit).body).toBeInstanceOf(FormData);
  });

  it("includes Authorization header when token exists", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 1, status: "pending", total_rows: 10, message: "" }),
    } as Response);

    const file = new File(["data"], "test.csv", { type: "text/csv" });
    await uploadFile(file, "pos");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect(
      ((options as RequestInit).headers as Record<string, string>)["Authorization"]
    ).toBe("Bearer test-token");
  });

  it("returns IngestionJob with pending status", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 5, status: "pending", total_rows: null, message: "" }),
    } as Response);

    const file = new File(["data"], "upload.csv", { type: "text/csv" });
    const result = await uploadFile(file, "pos");

    expect(result.id).toBe("5");
    expect(result.status).toBe("pending");
    expect(result.fileName).toBe("upload.csv");
    expect(result.sourceType).toBe("pos");
  });

  it("throws when server returns non-ok status", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Only .csv files are accepted" }),
    } as Response);

    const file = new File(["data"], "bad.xlsx", { type: "application/vnd.ms-excel" });
    await expect(uploadFile(file, "pos")).rejects.toThrow("Only .csv files are accepted");
  });
});

// ── getJobStatus ──────────────────────────────────────────────────────────────

describe("getJobStatus", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls the correct status endpoint", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockStatusResponse);

    await getJobStatus("1");

    expect(apiFetch).toHaveBeenCalledWith("/ingestion/1/status/");
  });

  it('maps backend "running" to frontend "processing"', async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ ...mockStatusResponse, status: "running" });

    const result = await getJobStatus("1");

    expect(result.status).toBe("processing");
  });

  it("maps valid_rows to recordsProcessed", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockStatusResponse);

    const result = await getJobStatus("1");

    expect(result.recordsProcessed).toBe(3001);
    expect(result.recordsTotal).toBe(3036);
  });

  it("sets errorMessage for failed jobs", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({ ...mockStatusResponse, status: "failed" });

    const result = await getJobStatus("1");

    expect(result.status).toBe("failed");
    expect(result.errorMessage).not.toBeNull();
  });

  it("sets errorMessage summarising rejected and error rows when completed with issues", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockStatusResponse); // rejected_rows=25, error_rows=10

    const result = await getJobStatus("1");

    expect(result.errorMessage).toContain("25");
    expect(result.errorMessage).toContain("10");
  });

  it("errorMessage is null when completed with no issues", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue({
      ...mockStatusResponse,
      status: "completed",
      rejected_rows: 0,
      error_rows: 0,
    });

    const result = await getJobStatus("1");

    expect(result.errorMessage).toBeNull();
  });

  it("returns dates from backend response", async () => {
    const apiFetch = await getApiFetch();
    apiFetch.mockResolvedValue(mockStatusResponse);

    const result = await getJobStatus("1");

    expect(result.createdAt).toBe("2026-06-04T10:00:00Z");
    expect(result.updatedAt).toBe("2026-06-04T10:01:30Z");
  });
});
