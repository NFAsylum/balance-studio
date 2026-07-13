/** Thin client for the Balance Studio API. Base URL from NEXT_PUBLIC_API_URL. */

import type { EntitySchema } from "./schema";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** A field-override op list, applied on top of a plugin schema (see EntitySchema.with_overrides). */
export type SchemaOverrides = { fields?: Array<Record<string, unknown>> };

export type ConstraintKind = "range" | "sum_of_fields" | "forbidden_combo" | "required_tag" | "unique_across_set";
export type Constraint = { kind: ConstraintKind; params: Record<string, unknown> };

export type Preset = {
  id: string;
  name: string;
  domain: string;
  description: string;
  schema_overrides: SchemaOverrides;
  default_constraints: Array<Record<string, unknown>>;
  default_objectives: Objective[];
  default_visual_variant: string | null;
  sim_config: Record<string, unknown>;
};

export type Scenario = {
  id: string;
  domain: string;
  name: string;
  brief: string;
  n_entities: number;
  objectives: Objective[];
  head_event_seq: number;
  current_branch: string;
  visual_variant?: string | null;
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
      schema: EntitySchema;
      head_seq: number;
      at_seq: number;
    }>(`/scenarios/${id}${atSeq != null ? `?at_seq=${atSeq}` : ""}`),
  createScenario: (body: {
    domain: string;
    name: string;
    brief: string;
    n_entities: number;
    preset_id?: string | null;
    schema_overrides?: SchemaOverrides;
    constraints?: Constraint[];
    visual_variant?: string | null;
  }) => request<Scenario>("/scenarios", { method: "POST", body: JSON.stringify(body) }),
  listPresets: (domain?: string) =>
    request<{ presets: Preset[] }>(`/presets${domain ? `?domain=${encodeURIComponent(domain)}` : ""}`),
  getPreset: (id: string) => request<Preset>(`/presets/${encodeURIComponent(id)}`),
  generate: (domain: string, body: { n: number; constraints?: Constraint[]; user_intent?: string; schema_overrides?: SchemaOverrides }) =>
    request<{ entities: Array<Record<string, unknown>>; requested: number }>(`/domains/${domain}/generate`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  editEntity: (id: string, entityId: string, entity: Record<string, unknown>) =>
    request<EntityEvent>(`/scenarios/${id}/entities/${encodeURIComponent(entityId)}`, {
      method: "PATCH",
      body: JSON.stringify({ entity }),
    }),
  addEntity: (id: string, entity: Record<string, unknown>) =>
    request<EntityEvent>(`/scenarios/${id}/entities`, { method: "POST", body: JSON.stringify({ entity }) }),
  deleteEntity: (id: string, entityId: string) =>
    request<EntityEvent>(`/scenarios/${id}/entities/${encodeURIComponent(entityId)}`, { method: "DELETE" }),
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
  listBranches: (id: string) => request<{ branches: BranchInfo[] }>(`/scenarios/${id}/branches`),
  createBranch: (id: string, parent_seq: number, name: string) =>
    request<{ branch_id: string }>(`/scenarios/${id}/branches`, {
      method: "POST",
      body: JSON.stringify({ parent_seq, name }),
    }),
  diffBranches: (id: string, a: string, b: string) =>
    request<DiffReport>(`/scenarios/${id}/branches/${a}/diff/${b}`),
};

export type BranchInfo = { branch_id: string; name: string; head_seq: number; event_count: number };

export type DiffReport = {
  branch_a: string;
  branch_b: string;
  exclusive_events_a: number;
  exclusive_events_b: number;
  entities: { only_in_a: string[]; only_in_b: string[]; changed: string[] };
  metrics_diff: Record<string, { a: number | null; b: number | null }>;
};
