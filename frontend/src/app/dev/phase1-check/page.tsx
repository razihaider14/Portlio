"use client";

import { useSkills } from "@/lib/query/hooks";

/**
 * TEMPORARY Phase 1 integration-check page.
 *
 * This is not the Skills Dashboard (Phase 2); no SkillCard, no tier
 * badges, no styling beyond what's needed to read the numbers. It exists
 * only to prove, against a real running backend, that:
 *   - the fetch client (src/lib/api/client.ts) builds correct requests
 *   - useSkills (src/lib/query/hooks.ts) wires loading/error/success states
 *   - the TypeScript types in src/types/ actually match what the backend
 *     returns
 */
const CHECK_USERNAME = "razihaider14";

export default function SkillsIntegrationCheckPage() {
  const { data, isLoading, isError, error } = useSkills(CHECK_USERNAME);

  return (
    <main style={{ padding: 32, fontFamily: "monospace" }}>
      <h1>Phase 1 integration check: GET /skills/{CHECK_USERNAME}</h1>

      {isLoading && <p>Loading...</p>}

      {isError && (
        <p>
          Error: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      )}

      {data && (
        <dl>
          <dt>repository_count</dt>
          <dd>{data.repository_count}</dd>

          <dt>strengths count</dt>
          <dd>{data.strengths.length}</dd>

          <dt>weaknesses count</dt>
          <dd>{data.weaknesses.length}</dd>

          <dt>recommendations count</dt>
          <dd>{data.recommendations.length}</dd>

          <dt>first 5 skills</dt>
          <dd>
            <ul>
              {data.skills.slice(0, 5).map((skill) => (
                <li key={skill.name}>
                  {skill.name} — {skill.tier} ({skill.score}/{skill.max_score})
                </li>
              ))}
            </ul>
          </dd>
        </dl>
      )}
    </main>
  );
}
