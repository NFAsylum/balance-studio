# Mistura pt/en na UI e termos vagos ocasionais

**Severity:** Low
**Priority:** P3
**Category:** UX
**Source:** `ui/src/lib/i18n.tsx:70-71`, `core/iteration_engine.py` (details keys)

## Descrição

Vários itens de baixa severidade agrupados para não inflar o count:

### 1. UI: PT tem "domains" em inglês no meio de português (`ui/src/lib/i18n.tsx:71`)

```typescript
const PT: Dict = {
  ...
  domainsAvailable: "{n} domains disponíveis",   // "domínios" would be consistent
  loadingDomains: "carregando domains…",         // ditto
  ...
};
```

O CLAUDE.md linha 142 é explícito: "Português em docs, comentários pro humano; Inglês em
código, docstrings, prompts LLM." A UI é interface pro humano, então português consistente.

### 2. `MetricsPanel.tsx:76-77` usa "Metrics" hardcoded (não usa `useT`)

```typescript
<h2 className="text-lg font-semibold">Metrics</h2>
<Button size="sm" onClick={onRunFull} disabled={freshness === "computing"}>
    {freshness === "computing" ? "computing…" : "Run Full Simulation"}
</Button>
```

Enquanto o resto da página passou pelo i18n dictionary. Se um usuário PT ativou o locale,
ele vê "Cenários / Fases / entities / Metrics / Run Full Simulation" — mistura.

### 3. `IterationEngine._iterate` retorna `details["skipped_user_owned"]` — a chave é boa mas os counts em `_simulate` são genéricos

```python
# core/iteration_engine.py:139-148
return StepResult(
    phase="simulate",
    events_appended=1,
    details={
        "n_runs": report.n_runs,
        "winrate": winrate,
        "matchups_reused": report.matchups_reused,
        "matchups_computed": report.matchups_computed,
    },
)
```

OK aqui — nomes específicos. Mas em outros lugares:

```python
# core/iteration_engine.py:119, 130, 152
return StepResult(phase="design", events_appended=0, details={"skipped": "not empty"})
return StepResult(phase="simulate", events_appended=0, details={"skipped": "no entities"})
return StepResult(phase="judge", events_appended=0, details={"skipped": "no entities"})
```

`"skipped": "not empty"` é vago — não diz o que estava vazio. `"skipped": "no entities"`
é melhor mas ainda um free-string. Melhor um enum-like:

```python
details={"skip_reason": "state_has_entities"}
details={"skip_reason": "state_empty"}
```

### 4. `logger.info("skipping domains.%s (no get_simulator)", module.name)` (registry.py:30) — mensagem fica em inglês em lugar de PT (correto pelo guideline), mas usa "domains.%s" que é o path Python — bom.

Isso é OK, apenas notando.

## Risco

- **Usuário PT vê Portuglish** — piora percepção do produto.
- **Detalhes de skip são difíceis de agir** — free-string sinaliza "just a hint" quando
  poderiam ser códigos machine-readable.

## Fix sugerido

1. Traduzir `domains` para `domínios` no `PT` dict.
2. Levar o texto de `MetricsPanel.tsx` pro `i18n.tsx` (adicionar keys `metricsTitle`, `runFull`,
   `computing`).
3. Trocar `details["skipped"]` por `details["skip_reason"]` com valores enum-like fechados
   (`"empty_state"`, `"no_entities"`, `"no_metrics"`).

## Referências

- CLAUDE.md linha 142 (convenções de idioma).
- CLAUDE.md linha 144 (não usar termos vagos).
