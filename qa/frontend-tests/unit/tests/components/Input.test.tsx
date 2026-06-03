import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { Input } from "@/components/ui/Input";

describe("Input", () => {
  it("renders without label when label not given", () => {
    render(<Input id="x" placeholder="Enter value" />);
    expect(screen.queryByRole("label")).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter value")).toBeInTheDocument();
  });

  it("renders label linked to input", () => {
    render(<Input id="email" label="Email" />);
    const label = screen.getByText("Email");
    expect(label).toBeInTheDocument();
    expect(label.closest("label") ?? label).toBeInTheDocument();
  });

  it("accepts typed text", async () => {
    render(<Input id="name" />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "Hello");
    expect(input).toHaveValue("Hello");
  });

  it("shows error message", () => {
    render(<Input id="x" error="This field is required" />);
    expect(screen.getByText("This field is required")).toBeInTheDocument();
  });

  it("applies error border class when error provided", () => {
    render(<Input id="x" error="Bad" />);
    expect(screen.getByRole("textbox")).toHaveClass("border-red-500");
  });

  it("is disabled when disabled prop passed", () => {
    render(<Input id="x" disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });

  it("has green focus ring classes", () => {
    render(<Input id="x" />);
    expect(screen.getByRole("textbox")).toHaveClass("focus:ring-green-500");
  });
});
