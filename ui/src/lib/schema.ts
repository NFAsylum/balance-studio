/** TS mirror of core.entity_schema (as returned by GET /domains/{name}/schema). */

export type FieldKind = "num" | "cat" | "bool" | "tag_set" | "str" | "map";

export type FieldSpec = {
  name: string;
  kind: FieldKind;
  range?: [number, number] | null;
  enum?: string[] | null;
  min_len?: number | null;
  max_len?: number | null;
  required?: boolean;
  description?: string;
};

export type EntitySchema = { name: string; fields: FieldSpec[] };

export type EntityValue = Record<string, unknown>;

/** Return an inline validation error for a field value, or null if valid. */
export function validateField(field: FieldSpec, value: unknown): string | null {
  switch (field.kind) {
    case "num": {
      if (typeof value !== "number" || Number.isNaN(value)) return "must be a number";
      if (field.range) {
        const [min, max] = field.range;
        if (value < min || value > max) return `must be between ${min} and ${max}`;
      }
      return null;
    }
    case "cat":
      if (field.enum && !field.enum.includes(String(value))) return "invalid option";
      return null;
    case "bool":
      return typeof value === "boolean" ? null : "must be true or false";
    case "str": {
      const s = String(value ?? "");
      if (field.min_len != null && s.length < field.min_len) return `min ${field.min_len} chars`;
      if (field.max_len != null && s.length > field.max_len) return `max ${field.max_len} chars`;
      return null;
    }
    case "tag_set":
      return Array.isArray(value) ? null : "must be a list of tags";
    case "map":
      return value && typeof value === "object" && !Array.isArray(value) ? null : "must be a map";
    default:
      return null;
  }
}
