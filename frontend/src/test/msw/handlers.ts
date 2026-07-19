import { http, HttpResponse } from "msw";
import {
  sampleAnalyzeResponse,
  sampleGithubReposResponse,
  sampleSkillsResponse,
} from "@/lib/api/__fixtures__/sampleResponses";

const API_BASE = "http://localhost:8000";

/**
 * Default happy-path handlers. Individual tests override these per-test
 * with server.use(...) for error scenarios (see analyze-user.integration.test.tsx).
 */
export const handlers = [
  http.get(`${API_BASE}/skills/:username`, () => {
    return HttpResponse.json(sampleSkillsResponse);
  }),
  http.get(`${API_BASE}/analyze/:username`, () => {
    return HttpResponse.json(sampleAnalyzeResponse);
  }),
  http.get(`${API_BASE}/github/:username`, () => {
    return HttpResponse.json(sampleGithubReposResponse);
  }),
];

/** FastAPI's real error body shape: {"detail": "..."} (see backend/app/main.py). */
export function backendErrorResponse(status: number, detail: string) {
  return HttpResponse.json({ detail }, { status });
}
