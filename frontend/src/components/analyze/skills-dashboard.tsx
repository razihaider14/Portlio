"use client";

import * as React from "react";
import { notFound } from "next/navigation";
import { CircleCheck, FolderX, ListChecks, Sparkles, TriangleAlert } from "lucide-react";
import { CategoryFilter } from "@/components/skills/category-filter";
import { RecommendationsList } from "@/components/skills/recommendations-list";
import { SkillsDashboardSkeleton } from "@/components/skills/skills-dashboard-skeleton";
import { SkillsGrid } from "@/components/skills/skills-grid";
import { StrengthsList } from "@/components/skills/strengths-list";
import { WeaknessesList } from "@/components/skills/weaknesses-list";
import { AnalyzeErrorState } from "@/components/analyze/analyze-error-state";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { ApiError } from "@/lib/api/errors";
import { useSkills } from "@/lib/query/hooks";
import type { RuleCategory } from "@/types/category";

interface SkillsDashboardProps {
  username: string;
}

function DashboardStat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border p-4">
      <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
        <Icon aria-hidden="true" className="size-3.5" />
        {label}
      </div>
      <span className="text-2xl font-semibold tabular-nums">{value}</span>
    </div>
  );
}

export function SkillsDashboard({ username }: SkillsDashboardProps) {
  const { data, error, isLoading, refetch } = useSkills(username);
  const [selectedCategory, setSelectedCategory] =
    React.useState<RuleCategory | null>(null);

  if (isLoading) {
    return <SkillsDashboardSkeleton />;
  }

  if (error) {
    // A nonexistent GitHub user is a distinct, common outcome, route it to
    // Next's not-found.tsx rather than the generic error state below (see
    // src/components/analyze/analyze-error-state.tsx for why 404 is
    // deliberately excluded from that component's cases).
    if (error instanceof ApiError && error.isNotFound) {
      notFound();
    }

    return (
      <div className="flex flex-col gap-8">
        <PageHeader title={username} />
        <AnalyzeErrorState error={error} onRetry={() => refetch()} />
      </div>
    );
  }

  if (!data) {
    // Unreachable in practice (isLoading/error are exhaustive for useQuery
    // once `enabled` is true), but keeps this component soundly typed
    // without a non-null assertion.
    return null;
  }

  const skillCategories = Array.from(
    new Set(data.skills.map((skill) => skill.category)),
  );
  const filteredSkills = selectedCategory
    ? data.skills.filter((skill) => skill.category === selectedCategory)
    : data.skills;

  return (
    <div className="flex flex-col gap-10">
      <PageHeader
        title={username}
        description={`${data.repository_count} ${
          data.repository_count === 1 ? "repository" : "repositories"
        } analyzed`}
      />

      {data.repository_count === 0 ? (
        <EmptyState
          icon={FolderX}
          title="No public repositories"
          description="This GitHub account has no public repositories for SkillForge to analyze."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <DashboardStat
              icon={FolderX}
              label="Repositories"
              value={data.repository_count}
            />
            <DashboardStat
              icon={ListChecks}
              label="Skills"
              value={data.skills.length}
            />
            <DashboardStat
              icon={Sparkles}
              label="Strengths"
              value={data.strengths.length}
            />
            <DashboardStat
              icon={TriangleAlert}
              label="Weaknesses"
              value={data.weaknesses.length}
            />
          </div>

          <section className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Strengths</h2>
            <StrengthsList strengths={data.strengths} />
          </section>

          <section className="flex flex-col gap-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2 className="text-lg font-semibold">
                All skills ({data.skills.length})
              </h2>
              <CategoryFilter
                categories={skillCategories}
                selected={selectedCategory}
                onChange={setSelectedCategory}
              />
            </div>
            <SkillsGrid
              skills={filteredSkills}
              isFiltered={selectedCategory !== null}
            />
          </section>

          <section className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold">Weaknesses</h2>
            <WeaknessesList weaknesses={data.weaknesses} />
          </section>

          <section className="flex flex-col gap-4">
            <div className="flex items-center gap-1.5">
              <CircleCheck aria-hidden="true" className="text-muted-foreground size-4" />
              <h2 className="text-lg font-semibold">Recommendations</h2>
            </div>
            <RecommendationsList recommendations={data.recommendations} />
          </section>
        </>
      )}
    </div>
  );
}
