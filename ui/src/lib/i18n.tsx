"use client";
import * as React from "react";

/** Lightweight i18n — dictionary + context, no routing changes, no dependency.
 *
 * `useT()` returns `t(key, vars?)` plus the current locale and a setter. It works even without a
 * provider (defaults to English) so isolated component tests don't need to be wrapped. */

export type Locale = "en" | "pt";

export const LOCALE_STORAGE_KEY = "balance-studio.locale";

type Dict = Record<string, string>;

const EN: Dict = {
  tagline: "Collaborative human/LLM balance framework",
  loading: "loading…",
  loadError: "failed to load scenario",
  back: "Back",
  // home
  scenarios: "Scenarios",
  domainsAvailable: "{n} domains available",
  loadingDomains: "loading domains…",
  newScenario: "New scenario",
  createScenario: "Create scenario",
  domain: "Domain",
  pickDomain: "pick a domain",
  name: "Name",
  brief: "Brief",
  briefPlaceholder: "aggro cheap units",
  entitiesField: "Entities",
  creating: "creating…",
  create: "Create",
  noScenarios: "No scenarios yet — create the first.",
  noBrief: "no brief",
  events: "events",
  branch: "branch",
  // scenario board
  entities: "entities",
  history: "History",
  branches: "Branches",
  phase_design: "design",
  phase_simulate: "simulate",
  phase_judge: "judge",
  phase_iterate: "iterate",
  noEntities: 'No entities — run the "design" phase.',
  edit: "Edit",
  save: "Save",
  cancel: "Cancel",
  saving: "saving…",
  editHint: "Edit fields and Save — your change is recorded as a user event (LLM never overwrites it).",
  // history
  readOnlyAt: "Read-only state at #{seq}",
  backToHead: "back to head",
  // branches
  compare: "Compare",
  vs: "vs",
  pickTwo: "Pick two different branches.",
  // controls
  toggleTheme: "Toggle dark mode",
  language: "Language",
  // editor
  step_domain: "Domain & template",
  templateLabel: "Template",
  startBlank: "Start blank",
  step_fields: "Fields",
  step_constraints: "Cross-field & set rules",
  step_intent: "Generation intent",
  step_details: "Details",
  livePreview: "Live preview",
  layoutStyle: "layout style",
  defaultList: "Default (list)",
  customVariants: "Custom variants",
  pickDomainPreview: "Pick a domain to preview.",
  preview1: "Preview 1 entity",
  tryAgain: "Try again",
  generating: "generating…",
  reset: "Reset",
  generatedPreview: "generated preview",
  fixInvalid: "Fix invalid fields before creating.",
  generateAndCreate: "Generate {n} & create",
  addField: "Add field",
  addConstraint: "Add constraint",
  entitiesCount: "Entities: {n}",
  themeBrief: "Theme brief",
  designerReceives: "The Designer will receive:",
  nothingYet: "(nothing yet)",
  // hero
  heroTitle: "Balance any game, collaboratively",
  heroBody:
    "Design entities with an LLM, simulate them deterministically, and tune for balance — card games, RPG bestiaries, or team rosters. Same engine, swap the plugin.",
  trySample: "Try a sample card game",
  buildingExample: "building example…",
  startScratch: "Start from scratch",
  // board
  rawJson: "raw JSON",
  hideRaw: "hide raw",
};

const PT: Dict = {
  tagline: "Framework de balance colaborativo humano + LLM",
  loading: "carregando…",
  loadError: "erro ao carregar o cenário",
  back: "Voltar",
  // home
  scenarios: "Cenários",
  domainsAvailable: "{n} domains disponíveis",
  loadingDomains: "carregando domains…",
  newScenario: "Novo cenário",
  createScenario: "Criar cenário",
  domain: "Domínio",
  pickDomain: "escolha um domínio",
  name: "Nome",
  brief: "Brief",
  briefPlaceholder: "unidades baratas agressivas",
  entitiesField: "Entidades",
  creating: "criando…",
  create: "Criar",
  noScenarios: "Nenhum cenário ainda — crie o primeiro.",
  noBrief: "sem brief",
  events: "eventos",
  branch: "branch",
  // scenario board
  entities: "entidades",
  history: "Histórico",
  branches: "Branches",
  phase_design: "projetar",
  phase_simulate: "simular",
  phase_judge: "avaliar",
  phase_iterate: "iterar",
  noEntities: 'Nenhuma entidade — rode a fase "design".',
  edit: "Editar",
  save: "Salvar",
  cancel: "Cancelar",
  saving: "salvando…",
  editHint: "Edite os campos e Salve — sua mudança vira um evento de usuário (o LLM nunca sobrescreve).",
  // history
  readOnlyAt: "Estado somente-leitura em #{seq}",
  backToHead: "voltar ao head",
  // branches
  compare: "Comparar",
  vs: "vs",
  pickTwo: "Escolha duas branches diferentes.",
  // controls
  toggleTheme: "Alternar modo escuro",
  language: "Idioma",
  // editor
  step_domain: "Domínio & template",
  templateLabel: "Template",
  startBlank: "Começar do zero",
  step_fields: "Campos",
  step_constraints: "Regras entre campos & de conjunto",
  step_intent: "Intenção de geração",
  step_details: "Detalhes",
  livePreview: "Prévia ao vivo",
  layoutStyle: "estilo de layout",
  defaultList: "Padrão (lista)",
  customVariants: "Variantes customizadas",
  pickDomainPreview: "Escolha um domínio para pré-visualizar.",
  preview1: "Pré-visualizar 1 entidade",
  tryAgain: "Tentar de novo",
  generating: "gerando…",
  reset: "Limpar",
  generatedPreview: "prévia gerada",
  fixInvalid: "Corrija os campos inválidos antes de criar.",
  generateAndCreate: "Gerar {n} & criar",
  addField: "Adicionar campo",
  addConstraint: "Adicionar restrição",
  entitiesCount: "Entidades: {n}",
  themeBrief: "Brief temático",
  designerReceives: "O Designer vai receber:",
  nothingYet: "(nada ainda)",
  // hero
  heroTitle: "Balanceie qualquer jogo, de forma colaborativa",
  heroBody:
    "Projete entidades com um LLM, simule de forma determinística e ajuste o balanceamento — card games, bestiários de RPG ou composições de time. Mesmo motor, troca o plugin.",
  trySample: "Testar um card game de exemplo",
  buildingExample: "montando exemplo…",
  startScratch: "Começar do zero",
  // board
  rawJson: "JSON bruto",
  hideRaw: "ocultar bruto",
};

const DICTS: Record<Locale, Dict> = { en: EN, pt: PT };

export type TranslateFn = (key: keyof typeof EN, vars?: Record<string, string | number>) => string;

function translate(locale: Locale, key: string, vars?: Record<string, string | number>): string {
  const template = DICTS[locale][key] ?? DICTS.en[key] ?? key;
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

type LocaleContextValue = { locale: Locale; setLocale: (l: Locale) => void; t: TranslateFn };

const LocaleContext = React.createContext<LocaleContextValue | null>(null);

function detectInitial(): Locale {
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (stored === "en" || stored === "pt") return stored;
    if (navigator.language?.toLowerCase().startsWith("pt")) return "pt";
  } catch {
    /* SSR or storage unavailable */
  }
  return "en";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = React.useState<Locale>("en");

  // Resolve the real locale after mount (avoids SSR/client hydration mismatch).
  React.useEffect(() => setLocaleState(detectInitial()), []);

  const setLocale = React.useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
    } catch {
      /* storage unavailable */
    }
  }, []);

  const value = React.useMemo<LocaleContextValue>(
    () => ({ locale, setLocale, t: (key, vars) => translate(locale, key as string, vars) }),
    [locale, setLocale]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useT(): LocaleContextValue {
  const ctx = React.useContext(LocaleContext);
  if (ctx) return ctx;
  // No provider (e.g. isolated unit test) — default to English, no-op setter.
  return { locale: "en", setLocale: () => {}, t: (key, vars) => translate("en", key as string, vars) };
}
