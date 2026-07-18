import { describe, expect, it } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/errors";
import {
  createQueryClient,
  QUERY_STALE_TIME_MS,
  shouldRetryQuery,
} from "@/lib/query/queryClient";

describe("shouldRetryQuery", () => {
  it("never retries a 404 (not found)", () => {
    const error = new ApiError("not found", { status: 404 });
    expect(shouldRetryQuery(0, error)).toBe(false);
  });

  it("never retries a 429 (rate limited), even on the first failure", () => {
    const error = new ApiError("rate limited", { status: 429 });
    expect(shouldRetryQuery(0, error)).toBe(false);
  });

  it("retries a 503 (service unavailable) while under the max retry count", () => {
    const error = new ApiError("unavailable", { status: 503 });
    expect(shouldRetryQuery(0, error)).toBe(true);
    expect(shouldRetryQuery(1, error)).toBe(true);
  });

  it("stops retrying a 503 once the max retry count is reached", () => {
    const error = new ApiError("unavailable", { status: 503 });
    expect(shouldRetryQuery(2, error)).toBe(false);
  });

  it("retries a network error while under the max retry count", () => {
    const error = new ApiError("offline", { status: 0, isNetworkError: true });
    expect(shouldRetryQuery(0, error)).toBe(true);
  });

  it("does not retry an unrelated HTTP error like 500 (not one of the three known statuses)", () => {
    const error = new ApiError("server error", { status: 500 });
    expect(shouldRetryQuery(0, error)).toBe(false);
  });

  it("falls back to default-retry behavior for a non-ApiError throw", () => {
    expect(shouldRetryQuery(0, new Error("unexpected bug"))).toBe(true);
    expect(shouldRetryQuery(1, new Error("unexpected bug"))).toBe(true);
  });

  it("still respects the max retry count for non-ApiError throws", () => {
    expect(shouldRetryQuery(2, new Error("unexpected bug"))).toBe(false);
  });
});

describe("createQueryClient", () => {
  it("returns a real QueryClient configured with the 5 minute staleTime", () => {
    const client = createQueryClient();
    expect(client).toBeInstanceOf(QueryClient);
    expect(QUERY_STALE_TIME_MS).toBe(5 * 60 * 1000);
    expect(client.getDefaultOptions().queries?.staleTime).toBe(
      QUERY_STALE_TIME_MS,
    );
  });

  it("wires shouldRetryQuery as the retry function", () => {
    const client = createQueryClient();
    expect(client.getDefaultOptions().queries?.retry).toBe(shouldRetryQuery);
  });
});
