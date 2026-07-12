"use client";
import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { type EntitySchema, type EntityValue, type FieldSpec, validateField } from "@/lib/schema";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";

/** Generic, schema-driven entity form. Both domains render through this one component. */
export function EntityEditor({
  schema,
  value,
  onChange,
}: {
  schema: EntitySchema;
  value: EntityValue;
  onChange: (next: EntityValue) => void;
}) {
  const setField = (name: string, v: unknown) => onChange({ ...value, [name]: v });

  return (
    <div className="flex flex-col gap-4">
      {schema.fields.map((field) => (
        <Field key={field.name} field={field} value={value[field.name]} onChange={(v) => setField(field.name, v)} />
      ))}
    </div>
  );
}

function Field({ field, value, onChange }: { field: FieldSpec; value: unknown; onChange: (v: unknown) => void }) {
  const error = validateField(field, value);
  return (
    <label className="flex flex-col gap-1 text-sm" data-testid={`field-${field.name}`}>
      <span className="font-medium">
        {field.name}
        {field.required === false && <span className="ml-1 text-xs text-muted-foreground">(optional)</span>}
      </span>
      {field.description && <span className="text-xs text-muted-foreground">{field.description}</span>}
      <FieldControl field={field} value={value} onChange={onChange} />
      {error && (
        <span role="alert" className="text-xs text-red-600">
          {error}
        </span>
      )}
    </label>
  );
}

function FieldControl({ field, value, onChange }: { field: FieldSpec; value: unknown; onChange: (v: unknown) => void }) {
  switch (field.kind) {
    case "num":
      return <NumField field={field} value={value as number} onChange={onChange} />;
    case "cat":
      return (
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        >
          {(field.enum ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );
    case "bool":
      return (
        <input
          type="checkbox"
          className="h-4 w-4"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
          aria-label={field.name}
        />
      );
    case "str":
      return <StrField field={field} value={String(value ?? "")} onChange={onChange} />;
    case "tag_set":
      return <TagSetField value={Array.isArray(value) ? (value as string[]) : []} onChange={onChange} />;
    case "map":
      return <MapField value={(value ?? {}) as Record<string, number>} onChange={onChange} />;
    default:
      return null;
  }
}

function NumField({ field, value, onChange }: { field: FieldSpec; value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-3">
      <Input
        type="number"
        className="w-28"
        value={Number.isFinite(value) ? value : ""}
        onChange={(e) => onChange(e.target.value === "" ? NaN : Number(e.target.value))}
        aria-label={field.name}
      />
      {field.range && (
        <Slider
          className="max-w-xs"
          min={field.range[0]}
          max={field.range[1]}
          step={1}
          value={[Number.isFinite(value) ? value : field.range[0]]}
          onValueChange={(v) => onChange(v[0])}
        />
      )}
    </div>
  );
}

function StrField({ field, value, onChange }: { field: FieldSpec; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1">
      <textarea
        className="min-h-[38px] rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        value={value}
        maxLength={field.max_len ?? undefined}
        onChange={(e) => onChange(e.target.value)}
        aria-label={field.name}
      />
      {field.max_len != null && (
        <span className="text-right text-xs text-muted-foreground">
          {value.length}/{field.max_len}
        </span>
      )}
    </div>
  );
}

function TagSetField({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [pending, setPending] = React.useState("");
  const add = () => {
    const tag = pending.trim();
    if (tag && !value.includes(tag)) onChange([...value, tag]);
    setPending("");
  };
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-1">
        {value.map((tag) => (
          <span key={tag} className="inline-flex items-center gap-1 rounded bg-muted px-2 py-0.5 text-xs">
            {tag}
            <button type="button" aria-label={`remove ${tag}`} onClick={() => onChange(value.filter((t) => t !== tag))}>
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
      <Input
        value={pending}
        placeholder="add tag + Enter"
        aria-label="add tag"
        onChange={(e) => setPending(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add();
          }
        }}
      />
    </div>
  );
}

function MapField({ value, onChange }: { value: Record<string, number>; onChange: (v: Record<string, number>) => void }) {
  const [key, setKey] = React.useState("");
  return (
    <div className="flex flex-col gap-2">
      {Object.entries(value).map(([k, v]) => (
        <div key={k} className="flex items-center gap-2" data-testid={`map-row-${k}`}>
          <span className="w-24 text-xs">{k}</span>
          <Input
            type="number"
            className="w-24"
            value={v}
            aria-label={`${k} value`}
            onChange={(e) => onChange({ ...value, [k]: Number(e.target.value) })}
          />
          <button type="button" aria-label={`remove ${k}`} onClick={() => {
            const next = { ...value };
            delete next[k];
            onChange(next);
          }}>
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      ))}
      <div className="flex items-center gap-2">
        <Input value={key} placeholder="key" aria-label="map key" className={cn("w-24")} onChange={(e) => setKey(e.target.value)} />
        <button
          type="button"
          className="text-xs text-muted-foreground underline"
          onClick={() => {
            if (key.trim()) {
              onChange({ ...value, [key.trim()]: 1 });
              setKey("");
            }
          }}
        >
          add key
        </button>
      </div>
    </div>
  );
}
