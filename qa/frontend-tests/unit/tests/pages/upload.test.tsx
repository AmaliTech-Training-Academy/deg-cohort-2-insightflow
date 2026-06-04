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
  id: "job-1", fileName: "sales.csv", sourceType: "pos",
  status: "pending", recordsTotal: null, recordsProcessed: null,
  errorMessage: null, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
};

const completedJob: IngestionJob = {
  ...pendingJob, status: "completed", recordsTotal: 1000, recordsProcessed: 1000,
};

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("NewUploadPage", () => {
  beforeEach(() => {
    vi.mocked(uploadsApi.uploadFile).mockResolvedValue(pendingJob);
    vi.mocked(uploadsApi.getJobStatus).mockResolvedValue(completedJob);
  });

  it("renders page heading", () => {
    wrap(<UploadPage />);
    expect(screen.getByText("New upload")).toBeInTheDocument();
  });

  it("renders CSV data source badge", () => {
    wrap(<UploadPage />);
    expect(screen.getByText("CSV File")).toBeInTheDocument();
  });

  it("renders file dropzone", () => {
    wrap(<UploadPage />);
    expect(screen.getByText(/Drop a file here/)).toBeInTheDocument();
  });

  it("upload button is disabled without a file", () => {
    wrap(<UploadPage />);
    expect(screen.getByRole("button", { name: /Start Upload/i })).toBeDisabled();
  });

  it("file input only accepts .csv", () => {
    const { container } = wrap(<UploadPage />);
    const input = container.querySelector("input[type='file']");
    expect(input).toHaveAttribute("accept", ".csv");
  });

  it("shows file name after selection", async () => {
    wrap(<UploadPage />);
    const file = new File(["id,amount\n1,100"], "data.csv", { type: "text/csv" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    await userEvent.upload(input, file);
    expect(screen.getByText("data.csv")).toBeInTheDocument();
  });

  it("upload button enabled after file selected", async () => {
    wrap(<UploadPage />);
    const file = new File(["id\n1"], "upload.csv", { type: "text/csv" });
    await userEvent.upload(document.querySelector("input[type='file']") as HTMLInputElement, file);
    expect(screen.getByRole("button", { name: /Start Upload/i })).toBeEnabled();
  });

  it("shows file requirements card", () => {
    wrap(<UploadPage />);
    expect(screen.getByText("File requirements")).toBeInTheDocument();
    expect(screen.getByText(/CSV only/)).toBeInTheDocument();
  });

  it("shows job status card after successful upload", async () => {
    wrap(<UploadPage />);
    const file = new File(["id\n1"], "sales.csv", { type: "text/csv" });
    await userEvent.upload(document.querySelector("input[type='file']") as HTMLInputElement, file);
    await userEvent.click(screen.getByRole("button", { name: /Start Upload/i }));
    await waitFor(() => expect(screen.getByText("Upload Status")).toBeInTheDocument());
  });
});
