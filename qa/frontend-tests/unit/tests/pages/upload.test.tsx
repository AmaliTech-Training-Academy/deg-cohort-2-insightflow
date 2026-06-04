import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import UploadPage from "@/app/(app)/uploads/new/page";
import * as uploadsApi from "@/api/uploads";
import type { IngestionJob } from "@/types";

vi.mock("@/api/uploads");
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    <a href={href} {...props}>{children}</a>,
}));

const pendingJob: IngestionJob = {
  id: "job-1",
  fileName: "sales.csv",
  sourceType: "pos",
  status: "pending",
  recordsTotal: 1000,
  recordsProcessed: null,
  rejectedRows: 0,
  errorRows: 0,
  errorMessage: null,
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const completedJob: IngestionJob = {
  ...pendingJob,
  status: "completed",
  recordsProcessed: 990,
  rejectedRows: 7,
  errorRows: 3,
};

const failedJob: IngestionJob = {
  ...pendingJob,
  status: "failed",
  errorMessage: "Worker stopped unexpectedly",
};

const CSV_HEADER =
  "transaction_id,date,store_id,cashier_id,product_sku,quantity,unit_price,discount_applied,total\n" +
  "1001,2025-01-01,1,2,PROD-001,3,10.00,0.00,30.00\n";

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

// ── Step 1: Select ────────────────────────────────────────────────────────────

describe("NewUploadPage — Step 1: Select", () => {
  beforeEach(() => {
    vi.mocked(uploadsApi.uploadFile).mockResolvedValue(pendingJob);
    vi.mocked(uploadsApi.getJobStatus).mockResolvedValue(completedJob);
  });

  it("renders page heading", () => {
    wrap(<UploadPage />);
    expect(screen.getByText("New upload")).toBeInTheDocument();
  });

  it("renders the 5-step stepper", () => {
    wrap(<UploadPage />);
    ["Select", "Preview", "Upload", "Process", "Summary"].forEach((label) =>
      expect(screen.getByText(label)).toBeInTheDocument()
    );
  });

  it("renders the file dropzone", () => {
    wrap(<UploadPage />);
    expect(screen.getByText(/Drop a file here/i)).toBeInTheDocument();
  });

  it("renders Expected format section with all POS columns", () => {
    wrap(<UploadPage />);
    expect(screen.getByText("Expected format")).toBeInTheDocument();
    [
      "transaction_id", "date", "store_id", "cashier_id",
      "product_sku", "quantity", "unit_price", "discount_applied", "total",
    ].forEach((col) => expect(screen.getByText(col)).toBeInTheDocument());
  });

  it("Next button is disabled without a file", () => {
    wrap(<UploadPage />);
    expect(screen.getByRole("button", { name: /^next$/i })).toBeDisabled();
  });

  it("file input accepts only .csv", () => {
    const { container } = wrap(<UploadPage />);
    const input = container.querySelector("input[type='file']");
    expect(input).toHaveAttribute("accept", ".csv");
  });

  it("shows file name after selection", async () => {
    const { container } = wrap(<UploadPage />);
    const file = new File([CSV_HEADER], "sales.csv", { type: "text/csv" });
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
    await waitFor(() => expect(screen.getByText("sales.csv")).toBeInTheDocument());
  });

  it("Next button enabled after valid CSV selected", async () => {
    const { container } = wrap(<UploadPage />);
    const file = new File([CSV_HEADER], "sales.csv", { type: "text/csv" });
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^next$/i })).toBeEnabled()
    );
  });

  it("shows missing columns error for invalid CSV", async () => {
    const { container } = wrap(<UploadPage />);
    const file = new File(["id,amount\n1,100\n"], "bad.csv", { type: "text/csv" });
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByText(/Missing required columns/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: /^next$/i })).toBeDisabled();
  });
});

// ── Step 2: Preview ───────────────────────────────────────────────────────────

describe("NewUploadPage — Step 2: Preview", () => {
  beforeEach(() => {
    vi.mocked(uploadsApi.uploadFile).mockResolvedValue(pendingJob);
    vi.mocked(uploadsApi.getJobStatus).mockResolvedValue(completedJob);
  });

  async function advanceToPreview() {
    const { container } = wrap(<UploadPage />);
    const file = new File([CSV_HEADER], "sales.csv", { type: "text/csv" });
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^next$/i })).toBeEnabled()
    );
    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    return container;
  }

  it("shows preview heading with filename", async () => {
    await advanceToPreview();
    await waitFor(() => expect(screen.getByText(/Previewing/)).toBeInTheDocument());
    expect(screen.getByText("sales.csv")).toBeInTheDocument();
  });

  it("shows Back and Upload file buttons", async () => {
    await advanceToPreview();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /back/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /upload file/i })).toBeInTheDocument();
    });
  });

  it("shows CSV column headers in preview table", async () => {
    await advanceToPreview();
    await waitFor(() =>
      expect(screen.getByText("transaction_id")).toBeInTheDocument()
    );
  });

  it("Back button returns to Step 1", async () => {
    await advanceToPreview();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /back/i })).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole("button", { name: /back/i }));
    await waitFor(() =>
      expect(screen.getByText("Expected format")).toBeInTheDocument()
    );
  });
});

// ── Step 5: Summary ───────────────────────────────────────────────────────────

describe("NewUploadPage — Step 5: Summary", () => {
  async function runToSummary(job: IngestionJob) {
    vi.mocked(uploadsApi.uploadFile).mockResolvedValue(pendingJob);
    vi.mocked(uploadsApi.getJobStatus).mockResolvedValue(job);

    const { container } = wrap(<UploadPage />);
    const file = new File([CSV_HEADER], "sales.csv", { type: "text/csv" });
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /^next$/i })).toBeEnabled()
    );
    await userEvent.click(screen.getByRole("button", { name: /^next$/i }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /upload file/i })).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole("button", { name: /upload file/i }));
  }

  it("shows Ingestion complete for completed job", async () => {
    await runToSummary(completedJob);
    await waitFor(() =>
      expect(screen.getByText("Ingestion complete")).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });

  it("shows Inserted tile with valid_rows count", async () => {
    await runToSummary(completedJob);
    await waitFor(() => expect(screen.getByText("Inserted")).toBeInTheDocument(), { timeout: 5000 });
    expect(screen.getByText("990")).toBeInTheDocument();
  });

  it("shows FK misses tile when rejectedRows > 0", async () => {
    await runToSummary(completedJob);
    await waitFor(() => expect(screen.getByText("FK misses")).toBeInTheDocument(), { timeout: 5000 });
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("shows Format errors tile when errorRows > 0", async () => {
    await runToSummary(completedJob);
    await waitFor(() => expect(screen.getByText("Format errors")).toBeInTheDocument(), { timeout: 5000 });
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("shows Ingestion failed heading for failed job", async () => {
    await runToSummary(failedJob);
    await waitFor(() =>
      expect(screen.getByText("Ingestion failed")).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });

  it("shows error message for failed job", async () => {
    await runToSummary(failedJob);
    await waitFor(() =>
      expect(screen.getByText("Worker stopped unexpectedly")).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });

  it("shows Upload another file button on summary", async () => {
    await runToSummary(completedJob);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /upload another file/i })).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });
});
