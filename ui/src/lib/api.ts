/** Thin client for the Balance Studio API. Base URL from NEXT_PUBLIC_API_URL. */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Scenario = {
  id: string;
  domain: string;
  name: string;
  brief: string;
  n_entities: number;
  objectives: Objective[];
  head_event_seq: number;
  current_branch: string;
};

export type Objective = {
  metric_name: string;
  direction: "minimize" | "maximize" | "target";
  target_value?: number | null;
  weight: number;
};

export type EntityEvent = {
  seq: number;
  parent_seq: number | null;
  branch_id: string;
  timestamp: string;
  actor: "user" | "llm-designer" | "llm-judge" | "llm-iterator";
  kind: string;
  target: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listDomains: () => request<{ domains: string[] }>("/domains"),
  listScenarios: () => request<{ scenarios: Scenario[] }>("/scenarios"),
  getScenario: (id: string, atSeq?: number) =>
    request<{
      scenario: Scenario;
      entities: Record<string, Record<string, unknown>>;
      head_seq: number;
      at_seq: number;
    }>(`/scenarios/${id}${atSeq != null ? `?at_seq=${atSeq}` : ""}`),
  createScenario: (body: { domain: string; name: string; brief: string; n_entities: number }) =>
    request<Scenario>("/scenarios", { method: "POST", body: JSON.stringify(body) }),
  iterate: (id: string, phase: "design" | "simulate" | "judge" | "iterate") =>
    request<{ phase: string; events_appended: number; details: Record<string, unknown> }>(
      `/scenarios/${id}/iterate`,
      { method: "POST", body: JSON.stringify({ phase }) }
    ),
  history: (id: string) => request<{ events: EntityEvent[] }>(`/scenarios/${id}/history`),
  getSchema: (domain: string) => request<Record<string, unknown>>(`/domains/${domain}/schema`),
  listMetrics: (domain: string) =>
    request<{ metrics: { name: string; kind: string; description: string }[] }>(
      `/domains/${domain}/metrics`
    ),
  setObjectives: (id: string, objectives: Objective[]) =>
    request<{ objectives: Objective[] }>(`/scenarios/${id}/objectives`, {
      method: "POST",
      body: JSON.stringify({ objectives }),
    }),
};
