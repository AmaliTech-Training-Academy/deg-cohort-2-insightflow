import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/ui/StatusBadge";

const STATUSES = [
  { status: "pending",    text: "Pending",    cls: "bg-yellow-100" },
  { status: "processing", text: "Processing", cls: "bg-blue-100" },
  { status: "completed",  text: "Completed",  cls: "bg-green-100" },
  { status: "failed",     text: "Failed",     cls: "bg-red-100" },
  { status: "healthy",    text: "Healthy",    cls: "bg-green-100" },
  { status: "degraded",   text: "Degraded",   cls: "bg-yellow-100" },
  { status: "down",       text: "Down",       cls: "bg-red-100" },
] as const;

describe("StatusBadge", () => {
  STATUSES.forEach(({ status, text, cls }) => {
    it(`renders ${status} badge with correct label and colour`, () => {
      render(<StatusBadge status={status} />);
      const badge = screen.getByText(text);
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass(cls);
    });
  });

  it("uses custom label when provided", () => {
    render(<StatusBadge status="completed" label="Done ✓" />);
    expect(screen.getByText("Done ✓")).toBeInTheDocument();
  });

  it("renders as an inline span", () => {
    const { container } = render(<StatusBadge status="healthy" />);
    expect(container.firstChild?.nodeName).toBe("SPAN");
  });
});
