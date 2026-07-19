import * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { server } from "@/test/msw/server";
import { backendErrorResponse } from "@/test/msw/handlers";
import { shouldRetryQuery } from "@/lib/query/queryClient";
import { sampleSkillsResponse } from "@/lib/api/__fixtures__/sampleResponses";

const notFoundMock = vi.fn();
vi.mock("next/navigation", () => ({
  notFound: () => notFoundMock(),
}));

const { SkillsDashboard } = await import(
  "@/components/analyze/skills-dashboard"
);

const API_BASE = "http://localhost:8000";

function renderDashboard(username = "octocat") {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetryQuery, retryDelay: 0, gcTime: 0 },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <SkillsDashboard username={username} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  notFoundMock.mockReset();
});

afterEach(() => {
  server.resetHandlers();
});

describe("SkillsDashboard integration (real fetch through MSW)", () => {
  it("shows the loading skeleton, then the full dashboard on success", async () => {
    renderDashboard("octocat");

    // Loading state: the skeleton is rendered with aria-busy while the
    // request to the (mocked) real backend is in flight.
    expect(screen.getByText(/loading skill analysis/i)).toBeInTheDocument();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "octocat" })).toBeInTheDocument(),
    );

    // repository_count
    expect(
      screen.getByText(`${sampleSkillsResponse.repository_count} repositories analyzed`),
    ).toBeInTheDocument();

    // Skill count, strengths, weaknesses summary stats
    expect(
      screen.getByText(`All skills (${sampleSkillsResponse.skills.length})`),
    ).toBeInTheDocument();

    // strengths[], weaknesses[], recommendations[] all rendered
    expect(screen.getAllByText("Python").length).toBeGreaterThanOrEqual(1); // strength + skill
    expect(screen.getByText("CI/CD")).toBeInTheDocument(); // weakness
    expect(screen.getAllByText("FreeRTOS").length).toBeGreaterThanOrEqual(1); // recommendation
  });

  it("filters the skills grid by category without affecting strengths/weaknesses", async () => {
    const user = userEvent.setup();
    renderDashboard("octocat");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "octocat" })).toBeInTheDocument(),
    );

    // sampleSkillsResponse.skills has one "language" (Python) and one
    // "embedded" (ESP32) skill.
    await user.click(screen.getByRole("button", { name: "Embedded" }));

    expect(screen.getAllByText("ESP32").length).toBeGreaterThanOrEqual(1);
    // "Python" still appears once, in the Strengths section, but no longer
    // in the "All skills" grid.
    expect(screen.getAllByText("Python")).toHaveLength(1);
  });

  it("calls next/navigation's notFound() on a 404 response", async () => {
    server.use(
      http.get(`${API_BASE}/skills/:username`, () =>
        backendErrorResponse(404, "GitHub user not found."),
      ),
    );

    renderDashboard("nonexistent-user");

    await waitFor(() => expect(notFoundMock).toHaveBeenCalledTimes(1));
  });

  it("shows rate-limit messaging inline (not notFound) on a 429 response", async () => {
    server.use(
      http.get(`${API_BASE}/skills/:username`, () =>
        backendErrorResponse(429, "GitHub API rate limit exceeded."),
      ),
    );

    renderDashboard("octocat");

    await waitFor(() =>
      expect(screen.getByText("GitHub rate limit exceeded")).toBeInTheDocument(),
    );
    expect(notFoundMock).not.toHaveBeenCalled();
  });

  it("shows backend-unavailable messaging inline on a 503 response", async () => {
    server.use(
      http.get(`${API_BASE}/skills/:username`, () =>
        backendErrorResponse(503, "GitHub service is temporarily unavailable."),
      ),
    );

    renderDashboard("octocat");

    await waitFor(
      () => expect(screen.getByText("Backend unavailable")).toBeInTheDocument(),
      { timeout: 5000 },
    );
  });

  it("retrying after a 503 succeeds once the backend recovers", async () => {
    let callCount = 0;
    server.use(
      http.get(`${API_BASE}/skills/:username`, () => {
        callCount += 1;
        if (callCount <= 3) {
          // 1 initial attempt + 2 automatic retries (MAX_RETRIES=2) all fail...
          return backendErrorResponse(503, "GitHub service is temporarily unavailable.");
        }
        // ...then the person clicks "Try again" and the 4th call succeeds.
        return HttpResponse.json(sampleSkillsResponse);
      }),
    );

    const user = userEvent.setup();
    renderDashboard("octocat");

    await waitFor(
      () => expect(screen.getByText("Backend unavailable")).toBeInTheDocument(),
      { timeout: 5000 },
    );

    await user.click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "octocat" })).toBeInTheDocument(),
    );
    expect(callCount).toBe(4);
  });

  it("shows the 'no public repositories' empty state when repository_count is 0", async () => {
    server.use(
      http.get(`${API_BASE}/skills/:username`, () =>
        HttpResponse.json({
          repository_count: 0,
          skills: [],
          strengths: [],
          weaknesses: [],
          recommendations: [],
        }),
      ),
    );

    renderDashboard("empty-account");

    await waitFor(() =>
      expect(screen.getByText("No public repositories")).toBeInTheDocument(),
    );
    // The stat grid / section headings shouldn't render alongside the
    // zero-repositories empty state.
    expect(screen.queryByText(/All skills/)).not.toBeInTheDocument();
  });
});
