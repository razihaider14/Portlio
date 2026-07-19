"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { githubUsernameError } from "@/lib/github-username";
import { cn } from "@/lib/utils";

interface UsernameFormProps {
  className?: string;
  /** Pre-fills the input, used by AnalyzeErrorState's "try another username" flow. */
  defaultValue?: string;
}

/**
 * A single-input form: GitHub username in, /analyze/[username] out.
 * Enter-to-submit works for free, this is a <form> with one text input
 * and a submit button, which is exactly the case the HTML spec triggers
 * implicit form submission on Enter for, so no keydown handler is needed.
 */
export function UsernameForm({
  className,
  defaultValue = "",
}: UsernameFormProps) {
  const router = useRouter();
  const [value, setValue] = React.useState(defaultValue);
  const [error, setError] = React.useState<string | null>(null);
  const errorId = React.useId();

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = value.trim();
    const validationError = githubUsernameError(trimmed);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    router.push(`/analyze/${encodeURIComponent(trimmed)}`);
  }

  return (
    <form
      onSubmit={handleSubmit}
      noValidate
      className={cn("flex flex-col gap-2", className)}
    >
      <div className="flex gap-2">
        <div className="flex-1">
          <label htmlFor="github-username" className="sr-only">
            GitHub username
          </label>
          <Input
            id="github-username"
            name="username"
            placeholder="e.g. octocat"
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            value={value}
            onChange={(event) => {
              setValue(event.target.value);
              if (error) setError(null);
            }}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
          />
        </div>
        <Button type="submit">
          <Search aria-hidden="true" />
          Analyze
        </Button>
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-destructive text-sm">
          {error}
        </p>
      )}
    </form>
  );
}
