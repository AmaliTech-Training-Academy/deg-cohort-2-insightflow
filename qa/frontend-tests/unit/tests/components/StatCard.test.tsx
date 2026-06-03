import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatCard } from "@/components/ui/StatCard";

function Icon() {
  return <span data-testid="icon">icon</span>;
}

describe("StatCard", () => {
  it("renders the label", () => {
    render(<StatCard label="Jobs Today" value={12} icon={<Icon />} />);
    expect(screen.getByText("Jobs Today")).toBeInTheDocument();
  });

  it("renders numeric value", () => {
    render(<StatCard label="Jobs Today" value={12} icon={<Icon />} />);
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("formats large numbers with locale separators", () => {
    render(<StatCard label="Records" value={48320} icon={<Icon />} />);
    expect(screen.getByText("48,320")).toBeInTheDocument();
  });

  it("renders string values as-is", () => {
    render(<StatCard label="Rate" value="99.9%" icon={<Icon />} />);
    expect(screen.getByText("99.9%")).toBeInTheDocument();
  });

  it("renders the icon", () => {
    render(<StatCard label="Jobs" value={0} icon={<Icon />} />);
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("does not render trend when not provided", () => {
    render(<StatCard label="Jobs" value={5} icon={<Icon />} />);
    expect(screen.queryByLabelText(/Trend/)).not.toBeInTheDocument();
  });

  it("renders positive trend with up arrow", () => {
    render(
      <StatCard label="Jobs" value={5} icon={<Icon />}
        trend={{ label: "20% success rate", positive: true }} />
    );
    const el = screen.getByLabelText("Trend: up 20% success rate");
    expect(el).toHaveTextContent("↑");
    expect(el).toHaveClass("text-green-600");
  });

  it("renders negative trend with down arrow", () => {
    render(
      <StatCard label="Jobs" value={2} icon={<Icon />}
        trend={{ label: "2 need review", positive: false }} />
    );
    const el = screen.getByLabelText("Trend: down 2 need review");
    expect(el).toHaveTextContent("↓");
    expect(el).toHaveClass("text-red-600");
  });

  it("applies custom icon background and color classes", () => {
    const { container } = render(
      <StatCard label="Test" value={1} icon={<Icon />}
        iconBg="bg-blue-50" iconColor="text-blue-600" />
    );
    expect(container.querySelector(".bg-blue-50.text-blue-600")).toBeInTheDocument();
  });
});
