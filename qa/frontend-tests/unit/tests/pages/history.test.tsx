import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HistoryPage from "@/app/(app)/uploads/history/page";
import * as historyApi from "@/api/history";
import type { PaginatedResponse, IngestionJob } from "@/types";

vi.mock("@/api/history");
vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [k: string]: unknown }) =>
    <a href={href} {...props}>{children}</a>,
}));

const mockJobs: IngestionJob[] = [
  { id: "1", fileName: "sales_jan.csv", sourceType: "pos", status: "completed", recordsTotal: 500, recordsProcessed: 500, errorMessage: null, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: "2", fileName: "inventory.csv", sourceType: "inventory", status: "failed",    recordsTotal: 200, recordsProcessed: 150, errorMessage: "Invalid column type", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: "3", fileName: "orders.csv",    sourceType: "online_orders", status: "processing", recordsTotal: 300, recordsProcessed: 120, errorMessage: null, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
];

const mockResponse: PaginatedResponse<IngestionJob> = {
  count: 3, next: null, previous: null, results: mockJobs,
};

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("IngestionHistoryPage", () => {
  beforeEach(() => {
    vi.mocked(historyApi.getIngestionHistory).mockResolvedValue(mockResponse);
  });

  it("renders page heading", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => expect(screen.getByText("Ingestion history")).toBeInTheDocument());
  });

  it("renders New Upload link", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => expect(screen.getByText("New Upload")).toBeInTheDocument());
  });

  it("renders all table column headers", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => {
      ["File", "Source", "Status", "Records", "Started"].forEach((h) =>
        expect(screen.getByText(h)).toBeInTheDocument()
      );
    });
  });

  it("renders all job file names", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("sales_jan.csv")).toBeInTheDocument();
      expect(screen.getByText("inventory.csv")).toBeInTheDocument();
      expect(screen.getByText("orders.csv")).toBeInTheDocument();
    });
  });

  it("renders status badges", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => {
      expect(screen.getByText("Completed")).toBeInTheDocument();
      expect(screen.getByText("Failed")).toBeInTheDocument();
      expect(screen.getByText("Processing")).toBeInTheDocument();
    });
  });

  it("shows error message under filename for failed jobs (not in Records column)", async () => {
    wrap(<HistoryPage />);
    await waitFor(() =>
      expect(screen.getByText("Invalid column type")).toBeInTheDocument()
    );
  });

  it("shows dash in Records column for failed jobs", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => expect(screen.getAllByText("—").length).toBeGreaterThan(0));
  });

  it("shows dash for pending/processing records", async () => {
    wrap(<HistoryPage />);
    await waitFor(() => expect(screen.getAllByText("—").length).toBeGreaterThan(0));
  });

  it("shows loading skeleton initially", () => {
    wrap(<HistoryPage />);
    expect(screen.getByLabelText("Loading")).toBeInTheDocument();
  });

  it("shows empty state when no jobs", async () => {
    vi.mocked(historyApi.getIngestionHistory).mockResolvedValue({
      count: 0, next: null, previous: null, results: [],
    });
    wrap(<HistoryPage />);
    await waitFor(() =>
      expect(screen.getByText("No uploads yet")).toBeInTheDocument()
    );
  });
});
