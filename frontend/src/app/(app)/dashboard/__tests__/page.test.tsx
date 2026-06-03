import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import DashboardPage from "../page";
import * as dashboardApi from "@/api/dashboard";
import type { DashboardStats } from "@/types";

vi.mock("@/api/dashboard");

const mockStats: DashboardStats = {
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
  ],
};

function renderWithQuery(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.mocked(dashboardApi.getDashboardStats).mockResolvedValue(mockStats);
  });

  it("shows loading state initially", () => {
    renderWithQuery(<DashboardPage />);
    expect(screen.getByLabelText("Loading dashboard")).toBeInTheDocument();
  });

  it("renders the page heading after loading", async () => {
    renderWithQuery(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByText("Dashboard")).toBeInTheDocument()
    );
  });

  it("renders all four stat cards after loading", async () => {
    renderWithQuery(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("Jobs Today")).toBeInTheDocument();
      expect(screen.getByText("Successful")).toBeInTheDocument();
      expect(screen.getByText("Failed")).toBeInTheDocument();
      expect(screen.getByText("Records Ingested")).toBeInTheDocument();
    });
  });

  it("displays correct stat values", async () => {
    renderWithQuery(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("12")).toBeInTheDocument();
      expect(screen.getByText("10")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(screen.getByText("48,320")).toBeInTheDocument();
    });
  });

  it("renders the source health table", async () => {
    renderWithQuery(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByText("Data Source Health")).toBeInTheDocument()
    );
    expect(screen.getByText("POS System")).toBeInTheDocument();
  });

  it("shows error banner when fetch fails", async () => {
    vi.mocked(dashboardApi.getDashboardStats).mockRejectedValue(
      new Error("Network error")
    );
    renderWithQuery(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument()
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Failed to load dashboard stats"
    );
  });

  it("shows success rate trend on successful jobs card", async () => {
    renderWithQuery(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByText(/83% success rate/)).toBeInTheDocument()
    );
  });

  it("shows failed jobs trend when failures exist", async () => {
    renderWithQuery(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByText(/2 need review/)).toBeInTheDocument()
    );
  });
});
