import type { Metadata } from "next";
import { SkillsDashboard } from "@/components/analyze/skills-dashboard";

interface AnalyzeUserPageProps {
  params: Promise<{ username: string }>;
}

export async function generateMetadata({
  params,
}: AnalyzeUserPageProps): Promise<Metadata> {
  const { username } = await params;
  return {
    title: `${username}'s skills | SkillForge`,
    description: `Detected skills, strengths, weaknesses, and recommendations for ${username}'s GitHub portfolio.`,
  };
}

/**
 * A plain Server Component. All the actual data fetching (useSkills, a
 * client-only hook) lives in SkillsDashboard, a Client Component, Next 15
 * makes `params` a Promise for Server Component pages, so unwrapping it
 * here and passing the resolved `username` down as a normal prop keeps
 * SkillsDashboard itself simple, without needing React's `use()` to
 * unwrap a Promise inside a "use client" file.
 */
export default async function AnalyzeUserPage({
  params,
}: AnalyzeUserPageProps) {
  const { username } = await params;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <SkillsDashboard username={username} />
    </main>
  );
}
