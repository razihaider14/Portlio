import { describe, expect, it } from "vitest";
import {
  githubUsernameError,
  isValidGithubUsername,
} from "@/lib/github-username";

describe("isValidGithubUsername", () => {
  it.each(["octocat", "torvalds", "a", "a1", "9numbers-start", "my-repo-name"])(
    "accepts %s",
    (username) => {
      expect(isValidGithubUsername(username)).toBe(true);
    },
  );

  it.each([
    ["", "empty string"],
    ["-octocat", "leading hyphen"],
    ["octocat-", "trailing hyphen"],
    ["octo--cat", "consecutive hyphens"],
    ["octo_cat", "underscore"],
    ["octo cat", "space"],
    ["octo.cat", "period"],
    ["a".repeat(40), "over 39 characters"],
  ])("rejects %s (%s)", (username) => {
    expect(isValidGithubUsername(username)).toBe(false);
  });

  it("accepts exactly 39 characters", () => {
    expect(isValidGithubUsername("a".repeat(39))).toBe(true);
  });
});

describe("githubUsernameError", () => {
  it("returns null for a valid username", () => {
    expect(githubUsernameError("octocat")).toBeNull();
  });

  it("trims whitespace before validating", () => {
    expect(githubUsernameError("  octocat  ")).toBeNull();
  });

  it("returns a specific message for an empty/whitespace-only input", () => {
    expect(githubUsernameError("   ")).toMatch(/enter a github username/i);
  });

  it("returns a specific message for a too-long username", () => {
    expect(githubUsernameError("a".repeat(40))).toMatch(/39 characters/);
  });

  it("returns a specific message for a leading/trailing hyphen", () => {
    expect(githubUsernameError("-octocat")).toMatch(/hyphen/i);
    expect(githubUsernameError("octocat-")).toMatch(/hyphen/i);
  });

  it("returns a specific message for consecutive hyphens", () => {
    expect(githubUsernameError("octo--cat")).toMatch(/consecutive hyphens/i);
  });

  it("returns a generic character message for other invalid characters", () => {
    expect(githubUsernameError("octo_cat")).toMatch(
      /letters, numbers, and hyphens/i,
    );
  });
});
