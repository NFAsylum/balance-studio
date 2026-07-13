"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Preset } from "@/lib/api";
import type { EntitySchema, FieldSpec } from "@/lib/schema";
import { applyOverrides, diffFields } from "@/lib/schema-overrides";
import { sampleEntity } from "@/lib/sample-entity";
import { DEFAULT_VIEW, getViewById, getViewsForDomain, isCustomView } from "@/domain-views/registry";
import { SafeView } from "@/domain-views/SafeView";
import { FieldBuilder, fieldsValid } from "@/components/editor/FieldBuilder";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

/** Scenario Editor (FASE 3) — pick a preset, review the schema, preview a layout, and create.
 * Field editing (T3.2), variant mapping (T3.3), constraints (T3.4) and intent (T3.5) build on
 * this skeleton. */
export default function NewScenarioPage() {
  const router = useRouter();
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.listDomains });

  const [domain, setDomain] = React.useState<string>("");
  const [presetId, setPresetId] = React.useState<string | null>(null);
  const [fields, setFields] = React.useState<FieldSpec[]>([]);
  const [variant, setVariant] = React.useState<string | null>(null);
  const [name, setName] = React.useState("New scenario");
  const [brief, setBrief] = React.useState("");
  const [n, setN] = React.useState(8);

  const schemaQ = useQuery({
    queryKey: ["schema", domain],
    queryFn: () => api.getSchema(domain) as Promise<EntitySchema>,
    enabled: !!domain,
  });
  const presetsQ = useQuery({
    queryKey: ["presets", domain],
    queryFn: () => api.listPresets(domain),
    enabled: !!domain,
  });

  const baseFields = schemaQ.data?.fields ?? [];
  const presets = presetsQ.data?.presets ?? [];

  // When the base schema arrives (new domain), start blank from it.
  React.useEffect(() => {
    if (schemaQ.data) {
      setFields(schemaQ.data.fields);
      setPresetId(null);
      setVariant(null);
    }
  }, [schemaQ.data]);

  const applyPreset = async (preset: Preset | null) => {
    if (!preset) {
      setPresetId(null);
      setFields(baseFields);
      setVariant(null);
      return;
    }
    setPresetId(preset.id);
    setFields(applyOverrides(baseFields, preset.schema_overrides));
    setVariant(preset.default_visual_variant);
    if (preset.name) setName(preset.name);
  };

  const effectiveSchema: EntitySchema = { name: schemaQ.data?.name ?? "Entity", fields };
  const view = getViewById(variant ?? "") ?? DEFAULT_VIEW;

  const create = useMutation({
    mutationFn: async () => {
      const preset = presets.find((p) => p.id === presetId) ?? null;
      const start = preset ? applyOverrides(baseFields, preset.schema_overrides) : baseFields;
      return api.createScenario({
        domain,
        name,
        brief,
        n_entities: n,
        preset_id: presetId,
        schema_overrides: diffFields(start, fields),
        visual_variant: variant,
      });
    },
    onSuccess: (scenario) => router.push(`/scenarios/${scenario.id}`),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">New scenario</h1>
        <Button asChild variant="outline"><Link href="/">Cancel</Link></Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        {/* left: configuration */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader><CardTitle className="text-sm">1 · Domain & preset</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-3">
              <label className="flex flex-col gap-1 text-sm">
                Domain
                <Select value={domain} onValueChange={setDomain}>
                  <SelectTrigger><SelectValue placeholder="pick a domain" /></SelectTrigger>
                  <SelectContent>
                    {domains.data?.domains.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                  </SelectContent>
                </Select>
              </label>

              {domain && (
                <div className="flex flex-col gap-2">
                  <span className="text-sm">Preset</span>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant={presetId === null ? "default" : "outline"} onClick={() => applyPreset(null)}>
                      Start blank
                    </Button>
                    {presets.map((p) => (
                      <Button
                        key={p.id}
                        size="sm"
                        variant={presetId === p.id ? "default" : "outline"}
                        title={p.description}
                        onClick={() => applyPreset(p)}
                      >
                        {p.name}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {domain && (
            <Card>
              <CardHeader><CardTitle className="text-sm">2 · Fields ({fields.length})</CardTitle></CardHeader>
              <CardContent>
                <FieldBuilder fields={fields} onChange={setFields} />
              </CardContent>
            </Card>
          )}

          {domain && (
            <Card>
              <CardHeader><CardTitle className="text-sm">3 · Details</CardTitle></CardHeader>
              <CardContent className="flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-sm">Name<Input value={name} onChange={(e) => setName(e.target.value)} /></label>
                <label className="flex flex-col gap-1 text-sm">Brief<Input value={brief} onChange={(e) => setBrief(e.target.value)} placeholder="e.g. aggressive early-game deck" /></label>
                <label className="flex flex-col gap-2 text-sm">Entities: {n}<Slider value={[n]} min={1} max={30} step={1} onValueChange={(v) => setN(v[0])} /></label>
              </CardContent>
            </Card>
          )}
        </div>

        {/* right: live preview */}
        <div className="flex flex-col gap-3">
          <Card>
            <CardHeader className="flex flex-col gap-2">
              <CardTitle className="text-sm">Live preview</CardTitle>
              {domain && (
                <select
                  aria-label="layout style"
                  className="h-8 rounded-md border border-input bg-background px-2 text-sm"
                  value={variant ?? "default"}
                  onChange={(e) => setVariant(e.target.value === "default" ? null : e.target.value)}
                >
                  {(() => {
                    const views = getViewsForDomain(domain);
                    const domainViews = views.filter((v) => !isCustomView(v) && v.id !== "default");
                    const customViews = views.filter(isCustomView);
                    return (
                      <>
                        {domainViews.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                        {customViews.length > 0 && (
                          <optgroup label="Custom variants">
                            {customViews.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                          </optgroup>
                        )}
                        <option value="default">Default (list)</option>
                      </>
                    );
                  })()}
                </select>
              )}
            </CardHeader>
            <CardContent className="flex justify-center">
              {domain ? (
                <SafeView view={view} entity={sampleEntity(effectiveSchema)} schema={effectiveSchema} />
              ) : (
                <p className="py-8 text-sm text-muted-foreground">Pick a domain to preview.</p>
              )}
            </CardContent>
          </Card>

          <Button disabled={!domain || create.isPending || !fieldsValid(fields)} onClick={() => create.mutate()}>
            {create.isPending ? "creating…" : `Create scenario`}
          </Button>
          {!fieldsValid(fields) && domain && <p className="text-xs text-destructive">Fix invalid fields before creating.</p>}
          {create.isError && <p className="text-xs text-destructive">{String(create.error)}</p>}
        </div>
      </div>
    </div>
  );
}
