import { render, screen } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { SourceHealthTable } from "@/components/dashboard/SourceHealthTable";
import type { DataSource } from "@/types";

const NOW = new Date("2026-06-03T12:00:00Z").getTime();

const mockSources: DataSource[] = [
  { id: "1", name: "Store POS",          type: "pos",           lastSyncAt: new Date(NOW - 5 * 60_000).toISOString(),   status: "healthy" },
  { id: "2", name: "Warehouse Stock",    type: "inventory",     lastSyncAt: null,                                        status: "degraded" },
  { id: "3", name: "E-commerce Platform", type: "online_orders", lastSyncAt: new Date(NOW - 2 * 3_600_000).toISOString(), status: "down" },
];

describe("SourceHealthTable", () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(NOW); });
  afterEach(() => { vi.useRealTimers(); });

  it("renders the card title", () => {
    render(<SourceHealthTable sources={mockSources} />);
    expect(screen.getByText("Data Source Health")).toBeInTheDocument();
  });

  it("renders all source names", () => {
    render(<SourceHealthTable sources={mockSources} />);
    expect(screen.getByText("Store POS")).toBeInTheDocument();
    expect(screen.getByText("Warehouse Stock")).toBeInTheDocument();
    expect(screen.getByText("E-commerce Platform")).toBeInTheDocument();
  });

  it("renders human-readable type labels", () => {
    render(<SourceHealthTable sources={mockSources} />);
    expect(screen.getByText("POS")).toBeInTheDocument();
    expect(screen.getByText("Inventory")).toBeInTheDocument();
    expect(screen.getByText("Online Orders")).toBeInTheDocument();
  });

  it("shows Never for null lastSyncAt", () => {
    render(<SourceHealthTable sources={mockSources} />);
    expect(screen.getByText("Never")).toBeInTheDocument();
  });

  it("shows relative time for recent syncs", () => {
    render(<SourceHealthTable sources={mockSources} />);
    expect(screen.getByText("5m ago")).toBeInTheDocument();
    expect(screen.getByText("2h ago")).toBeInTheDocument();
  });

  it("renders status badges", () => {
    render(<SourceHealthTable sources={mockSources} />);
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("Degraded")).toBeInTheDocument();
    expect(screen.getByText("Down")).toBeInTheDocument();
  });

  it("renders empty table body when no sources", () => {
    const { container } = render(<SourceHealthTable sources={[]} />);
    expect(container.querySelectorAll("tbody tr")).toHaveLength(0);
  });

  it("renders table headers", () => {
    render(<SourceHealthTable sources={mockSources} />);
    ["Source", "Type", "Last Sync", "Status"].forEach((h) =>
      expect(screen.getByText(h)).toBeInTheDocument()
    );
  });
});
