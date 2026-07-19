import type { Metadata } from "next";
import { UsernameForm } from "@/components/analyze/username-form";

export const metadata: Metadata = {
  title: "Analyze a GitHub portfolio | SkillForge",
  description:
    "Enter a GitHub username to see detected skills, strengths, weaknesses, and recommendations.",
};

export default function AnalyzeEntryPage() {
  return (
    <main className="mx-auto flex min-h-svh max-w-xl flex-col items-center justify-center gap-6 px-6 py-16 text-center">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Analyze a GitHub portfolio
        </h1>
        <p className="text-muted-foreground text-sm">
          Enter a GitHub username to see its detected skills, strengths,
          weaknesses, and recommendations.
        </p>
      </div>
      <UsernameForm className="w-full" />
    </main>
  );
}
