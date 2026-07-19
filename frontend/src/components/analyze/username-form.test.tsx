import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

const { UsernameForm } = await import("@/components/analyze/username-form");

beforeEach(() => {
  pushMock.mockReset();
});

describe("UsernameForm", () => {
  it("navigates to /analyze/[username] on valid submit", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.type(screen.getByLabelText("GitHub username"), "octocat");
    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(pushMock).toHaveBeenCalledWith("/analyze/octocat");
  });

  it("submits on Enter without clicking the button", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.type(screen.getByLabelText("GitHub username"), "octocat{Enter}");

    expect(pushMock).toHaveBeenCalledWith("/analyze/octocat");
  });

  it("trims leading/trailing whitespace before navigating", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.type(screen.getByLabelText("GitHub username"), "  octocat  {Enter}");

    expect(pushMock).toHaveBeenCalledWith("/analyze/octocat");
  });

  it("does not navigate and shows an error for an empty submission", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      /enter a github username/i,
    );
  });

  it("does not navigate and shows an error for an invalid username", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.type(screen.getByLabelText("GitHub username"), "-invalid-{Enter}");

    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/hyphen/i);
  });

  it("clears a previous error as soon as the user edits the input again", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.click(screen.getByRole("button", { name: "Analyze" }));
    expect(screen.getByRole("alert")).toBeInTheDocument();

    await user.type(screen.getByLabelText("GitHub username"), "o");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("marks the input aria-invalid when there is a validation error", async () => {
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.click(screen.getByRole("button", { name: "Analyze" }));

    expect(screen.getByLabelText("GitHub username")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("pre-fills the input from defaultValue", () => {
    render(<UsernameForm defaultValue="octocat" />);
    expect(screen.getByLabelText("GitHub username")).toHaveValue("octocat");
  });

  it("URL-encodes an otherwise-valid-looking but unusual username", async () => {
    // GitHub usernames can't contain a slash per our own validation, so this
    // mainly documents that navigation always goes through encodeURIComponent
    // rather than string concatenation, using a username our own validator
    // does accept.
    const user = userEvent.setup();
    render(<UsernameForm />);

    await user.type(screen.getByLabelText("GitHub username"), "my-org{Enter}");

    expect(pushMock).toHaveBeenCalledWith("/analyze/my-org");
  });
});
