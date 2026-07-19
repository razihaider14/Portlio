/**
 * GitHub's actual username rules: alphanumeric characters or single
 * hyphens, may not begin or end with a hyphen, no consecutive hyphens,
 * max 39 characters. The lookahead after each hyphen enforces "no
 * consecutive hyphens" and "can't end with a hyphen" in one pass.
 */
const GITHUB_USERNAME_PATTERN =
  /^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$/;

export const GITHUB_USERNAME_MAX_LENGTH = 39;

export function isValidGithubUsername(username: string): boolean {
  return GITHUB_USERNAME_PATTERN.test(username);
}

/**
 * Returns a user-facing reason the username is invalid, or null if it's
 * valid. Checked in a specific order so the message matches the first rule
 * actually broken, rather than a generic "invalid username" for every case.
 */
export function githubUsernameError(rawUsername: string): string | null {
  const username = rawUsername.trim();

  if (username.length === 0) {
    return "Enter a GitHub username.";
  }
  if (username.length > GITHUB_USERNAME_MAX_LENGTH) {
    return `GitHub usernames are at most ${GITHUB_USERNAME_MAX_LENGTH} characters.`;
  }
  if (username.startsWith("-") || username.endsWith("-")) {
    return "GitHub usernames can't start or end with a hyphen.";
  }
  if (username.includes("--")) {
    return "GitHub usernames can't contain consecutive hyphens.";
  }
  if (!isValidGithubUsername(username)) {
    return "GitHub usernames can only contain letters, numbers, and hyphens.";
  }
  return null;
}
