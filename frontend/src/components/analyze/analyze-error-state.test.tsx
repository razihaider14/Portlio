import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalyzeErrorState } from "@/components/analyze/analyze-error-state";
import { ApiError } from "@/lib/api/errors";

describe("AnalyzeErrorState", () => {
  it("shows rate-limit messaging for a 429 ApiError", () => {
    render(
      <AnalyzeErrorState
        error={new ApiError("GitHub API rate limit exceeded.", { status: 429 })}
      />,
    );
    expect(screen.getByText("GitHub rate limit exceeded")).toBeInTheDocument();
  });

  it("shows backend-unavailable messaging for a 503 ApiError", () => {
    render(
      <AnalyzeErrorState
        error={
          new ApiError("GitHub service is temporarily unavailable.", {
            status: 503,
          })
        }
      />,
    );
    expect(screen.getByText("Backend unavailable")).toBeInTheDocument();
  });

  it("shows a connectivity message for a network ApiError", () => {
    render(
      <AnalyzeErrorState
        error={new ApiError("offline", { status: 0, isNetworkError: true })}
      />,
    );
    expect(screen.getByText("Can't reach SkillForge")).toBeInTheDocument();
  });

  it("falls back to a generic message for a non-ApiError exception", () => {
    render(<AnalyzeErrorState error={new Error("Something broke")} />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders as an alert region", () => {
    render(
      <AnalyzeErrorState
        error={new ApiError("x", { status: 429 })}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("renders a retry button when onRetry is provided, and calls it on click", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <AnalyzeErrorState error={new ApiError("x", { status: 503 })} onRetry={onRetry} />,
    );

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders no retry button when onRetry is omitted", () => {
    render(<AnalyzeErrorState error={new ApiError("x", { status: 503 })} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
