import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGetMock = vi.fn();
vi.mock("@/lib/api/client", () => ({
  apiGet: (...args: unknown[]) => apiGetMock(...args),
}));

// Imported after the mock so endpoints.ts picks up the mocked apiGet.
const { getAnalysis, getRepos, getSkills } = await import(
  "@/lib/api/endpoints"
);

describe("endpoints", () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiGetMock.mockResolvedValue({});
  });

  describe("getSkills", () => {
    it("calls GET /skills/{username} with include_content defaulting to false", async () => {
      await getSkills("octocat");

      expect(apiGetMock).toHaveBeenCalledWith("/skills/octocat", {
        include_content: false,
      });
    });

    it("propagates include_content=true when explicitly requested", async () => {
      await getSkills("octocat", true);

      expect(apiGetMock).toHaveBeenCalledWith("/skills/octocat", {
        include_content: true,
      });
    });

    it("URL-encodes the username", async () => {
      await getSkills("weird/name");

      expect(apiGetMock).toHaveBeenCalledWith(
        "/skills/weird%2Fname",
        expect.anything(),
      );
    });
  });

  describe("getAnalysis", () => {
    it("calls GET /analyze/{username} with include_content defaulting to false", async () => {
      await getAnalysis("octocat");

      expect(apiGetMock).toHaveBeenCalledWith("/analyze/octocat", {
        include_content: false,
      });
    });

    it("propagates include_content=true when explicitly requested", async () => {
      await getAnalysis("octocat", true);

      expect(apiGetMock).toHaveBeenCalledWith("/analyze/octocat", {
        include_content: true,
      });
    });
  });

  describe("getRepos", () => {
    it("calls GET /github/{username} with no query params at all", async () => {
      await getRepos("octocat");

      expect(apiGetMock).toHaveBeenCalledWith("/github/octocat");
      // Specifically: no include_content param, since the backend endpoint
      // doesn't accept one (see backend/app/main.py's get_github_user_repos).
      expect(apiGetMock).not.toHaveBeenCalledWith(
        "/github/octocat",
        expect.objectContaining({ include_content: expect.anything() }),
      );
    });
  });
});
