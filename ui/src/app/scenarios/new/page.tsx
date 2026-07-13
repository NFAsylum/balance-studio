"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Constraint, type Preset } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { EntitySchema, FieldSpec } from "@/lib/schema";
import { applyOverrides, diffFields } from "@/lib/schema-overrides";
import { checkConstraints } from "@/lib/constraints";
import { sampleEntity } from "@/lib/sample-entity";
import { DEFAULT_VIEW, getViewById, getViewsForDomain, isCustomView, isExampleView } from "@/domain-views/registry";
import { SafeView } from "@/domain-views/SafeView";
import { FieldBuilder, fieldsValid } from "@/components/editor/FieldBuilder";
import { ConstraintsEditor } from "@/components/editor/ConstraintsEditor";
import { DEFAULT_INTENT, IntentPanel, composeBrief, type Intent } from "@/components/editor/IntentPanel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

/** Scenario Editor (FASE 3): preset → fields → variant → constraints → intent → preview → create. */
export default function NewScenarioPage() {
  const router = useRouter();
  const { t } = useT();
  const domains = useQuery({ queryKey: ["domains"], queryFn: api.listDomains });

  const [domain, setDomain] = React.useState<string>("");
  const [presetId, setPresetId] = React.useState<string | null>(null);
  const [fields, setFields] = React.useState<FieldSpec[]>([]);
  const [variant, setVariant] = React.useState<string | null>(null);
  const [constraints, setConstraints] = React.useState<Constraint[]>([]);
  const [intent, setIntent] = React.useState<Intent>(DEFAULT_INTENT);
  const [name, setName] = React.useState("New scenario");
  const [n, setN] = React.useState(8);
  const [previewEntity, setPreviewEntity] = React.useState<Record<string, unknown> | null>(null);

  const schemaQ = useQuery({ queryKey: ["schema", domain], queryFn: () => api.getSchema(domain) as Promise<EntitySchema>, enabled: !!domain });
  const presetsQ = useQuery({ queryKey: ["presets", domain], queryFn: () => api.listPresets(domain), enabled: !!domain });
  const baseFields = schemaQ.data?.fields ?? [];
  const presets = presetsQ.data?.presets ?? [];

  React.useEffect(() => {
    if (schemaQ.data) {
      setFields(schemaQ.data.fields);
      setPresetId(null);
      setVariant(null);
      setConstraints([]);
      setPreviewEntity(null);
    }
  }, [schemaQ.data]);

  const applyPreset = (preset: Preset | null) => {
    setPreviewEntity(null);
    if (!preset) {
      setPresetId(null);
      setFields(baseFields);
      setVariant(null);
      setConstraints([]);
      return;
    }
    setPresetId(preset.id);
    setFields(applyOverrides(baseFields, preset.schema_overrides));
    setVariant(preset.default_visual_variant);
    setConstraints((preset.default_constraints ?? []) as Constraint[]);
    if (preset.name) setName(preset.name);
  };

  const effectiveSchema: EntitySchema = { name: schemaQ.data?.name ?? "Entity", fields };
  const view = getViewById(variant ?? "") ?? DEFAULT_VIEW;
  const startFields = () => {
    const preset = presets.find((p) => p.id === presetId) ?? null;
    return preset ? applyOverrides(baseFields, preset.schema_overrides) : baseFields;
  };
  const overrides = () => diffFields(startFields(), fields);

  const previewSample = previewEntity ?? sampleEntity(effectiveSchema);
  const violations = checkConstraints(previewSample, constraints);

  const previewOne = useMutation({
    mutationFn: () =>
      api.generate(domain, { n: 1, constraints, user_intent: composeBrief(intent), schema_overrides: overrides() }),
    onSuccess: (r) => setPreviewEntity(r.entities[0] ?? null),
  });

  const create = useMutation({
    mutationFn: () =>
      api.createScenario({
        domain,
        name,
        brief: composeBrief(intent),
        n_entities: n,
        preset_id: presetId,
        schema_overrides: overrides(),
        constraints,
        visual_variant: variant,
      }),
    onSuccess: (scenario) => router.push(`/scenarios/${scenario.id}`),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("newScenario")}</h1>
        <Button asChild variant="outline"><Link href="/">{t("cancel")}</Link></Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader><CardTitle className="text-sm">1 · {t("step_domain")}</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-3">
              <label className="flex flex-col gap-1 text-sm">
                {t("domain")}
                <Select value={domain} onValueChange={setDomain}>
                  <SelectTrigger><SelectValue placeholder={t("pickDomain")} /></SelectTrigger>
                  <SelectContent>{domains.data?.domains.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                </Select>
              </label>
              {domain && (
                <div className="flex flex-col gap-2">
                  <span className="text-sm">{t("templateLabel")}</span>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant={presetId === null ? "default" : "outline"} onClick={() => applyPreset(null)}>{t("startBlank")}</Button>
                    {presets.map((p) => (
                      <Button key={p.id} size="sm" variant={presetId === p.id ? "default" : "outline"} title={p.description} onClick={() => applyPreset(p)}>{p.name}</Button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {domain && (
            <>
              <Card>
                <CardHeader><CardTitle className="text-sm">2 · {t("step_fields")} ({fields.length})</CardTitle></CardHeader>
                <CardContent><FieldBuilder fields={fields} onChange={setFields} /></CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">3 · {t("step_constraints")}</CardTitle></CardHeader>
                <CardContent><ConstraintsEditor constraints={constraints} onChange={setConstraints} violations={violations} /></CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">4 · {t("step_intent")}</CardTitle></CardHeader>
                <CardContent><IntentPanel intent={intent} onChange={setIntent} /></CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">5 · {t("step_details")}</CardTitle></CardHeader>
                <CardContent className="flex flex-col gap-3">
                  <label className="flex flex-col gap-1 text-sm">{t("name")}<Input value={name} onChange={(e) => setName(e.target.value)} /></label>
                  <label className="flex flex-col gap-2 text-sm">{t("entitiesCount", { n })}<Slider value={[n]} min={1} max={30} step={1} onValueChange={(v) => setN(v[0])} /></label>
                </CardContent>
              </Card>
            </>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <Card>
            <CardHeader className="flex flex-col gap-2">
              <CardTitle className="text-sm">{t("livePreview")}</CardTitle>
              {domain && (
                <select aria-label={t("layoutStyle")} className="h-8 rounded-md border border-input bg-background px-2 text-sm" value={variant ?? "default"} onChange={(e) => setVariant(e.target.value === "default" ? null : e.target.value)}>
                  {(() => {
                    const views = getViewsForDomain(domain).filter((v) => !isExampleView(v));
                    return (
                      <>
                        {views.filter((v) => !isCustomView(v) && v.id !== "default").map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                        {views.filter(isCustomView).length > 0 && (
                          <optgroup label={t("customVariants")}>{views.filter(isCustomView).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}</optgroup>
                        )}
                        <option value="default">{t("defaultList")}</option>
                      </>
                    );
                  })()}
                </select>
              )}
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-3">
              {domain ? (
                <>
                  <SafeView view={view} entity={previewSample} schema={effectiveSchema} />
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" disabled={previewOne.isPending || !fieldsValid(fields)} onClick={() => previewOne.mutate()}>
                      {previewOne.isPending ? t("generating") : previewEntity ? t("tryAgain") : t("preview1")}
                    </Button>
                    {previewEntity && <Button size="sm" variant="ghost" onClick={() => setPreviewEntity(null)}>{t("reset")}</Button>}
                  </div>
                  {previewEntity && <span className="text-xs text-muted-foreground">{t("generatedPreview")}</span>}
                </>
              ) : (
                <p className="py-8 text-sm text-muted-foreground">{t("pickDomainPreview")}</p>
              )}
            </CardContent>
          </Card>

          <Button disabled={!domain || create.isPending || !fieldsValid(fields)} onClick={() => create.mutate()}>
            {create.isPending ? t("creating") : t("generateAndCreate", { n })}
          </Button>
          {!fieldsValid(fields) && domain && <p className="text-xs text-destructive">{t("fixInvalid")}</p>}
          {create.isError && <p className="text-xs text-destructive">{String(create.error)}</p>}
        </div>
      </div>
    </div>
  );
}
