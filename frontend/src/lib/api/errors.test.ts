import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api/errors";

describe("ApiError", () => {
  it("is a real Error instance (instanceof works)", () => {
    const error = new ApiError("boom", { status: 500 });
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.name).toBe("ApiError");
    expect(error.message).toBe("boom");
  });

  it("flags 404 as isNotFound and nothing else", () => {
    const error = new ApiError("not found", { status: 404 });
    expect(error.isNotFound).toBe(true);
    expect(error.isRateLimited).toBe(false);
    expect(error.isServiceUnavailable).toBe(false);
  });

  it("flags 429 as isRateLimited and nothing else", () => {
    const error = new ApiError("rate limited", { status: 429 });
    expect(error.isRateLimited).toBe(true);
    expect(error.isNotFound).toBe(false);
    expect(error.isServiceUnavailable).toBe(false);
  });

  it("flags 503 as isServiceUnavailable and nothing else", () => {
    const error = new ApiError("unavailable", { status: 503 });
    expect(error.isServiceUnavailable).toBe(true);
    expect(error.isNotFound).toBe(false);
    expect(error.isRateLimited).toBe(false);
  });

  describe("isRetryable", () => {
    it("is true for a network error regardless of status", () => {
      const error = new ApiError("offline", {
        status: 0,
        isNetworkError: true,
      });
      expect(error.isRetryable).toBe(true);
    });

    it("is true for 503", () => {
      const error = new ApiError("unavailable", { status: 503 });
      expect(error.isRetryable).toBe(true);
    });

    it("is false for 404", () => {
      const error = new ApiError("not found", { status: 404 });
      expect(error.isRetryable).toBe(false);
    });

    it("is false for 429", () => {
      const error = new ApiError("rate limited", { status: 429 });
      expect(error.isRetryable).toBe(false);
    });

    it("is false for an unrelated HTTP error, e.g. 500", () => {
      const error = new ApiError("server error", { status: 500 });
      expect(error.isRetryable).toBe(false);
    });
  });
});
