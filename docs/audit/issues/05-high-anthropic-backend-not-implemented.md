# Backend `anthropic` documentado mas não implementado

**Severity:** High
**Priority:** P1
**Category:** Design
**Source:** `core/llm_factory.py:33-37`, `CLAUDE.md:25`, `docs/architecture.md:119`, `pyproject.toml:11`

## Descrição

O CLAUDE.md prescreve claramente o Anthropic backend como parte do produto:

> Stack fixado: **Anthropic SDK, modelo `claude-sonnet-4-6`, `tool_use` obrigatório**
> (CLAUDE.md linha 33).

E:

> Cada hat tem `Fake*` (dev, sem custo) e `Anthropic*` (Sprint 6, real). Config switch via
> env var. (CLAUDE.md linha 25).

O `docs/architecture.md:119` documenta os protocols com "Cada um tem impl `Fake*` (dev) e
`Anthropic*` (Sprint 6)".

Mas o `llm_factory.py`:

```python
# core/llm_factory.py:33-37
if backend == "anthropic":
    raise NotImplementedError(
        "the 'anthropic' backend is not implemented — use LLM_BACKEND=fake or local"
    )
```

E `anthropic = "^0.40.0"` está no `pyproject.toml` mas `grep -rn "import anthropic" .`
retorna zero hits em código de produção. O `.env.example:5` prescreve `ANTHROPIC_API_KEY=sk-ant-...`
como se fosse suportado.

O README diz "Sprints 1-7 complete (core, 3 domains, event log + branching, multi-objective,
incremental cache, full UI, real local LLM)." — reconhecendo que Anthropic ficou de fora
mas sem retirar as promessas antigas da documentação.

## Risco

- **Expectativa quebrada** — CLAUDE.md e architecture.md permanecem enganosos. Se um
  próximo desenvolvedor (ou LLM em nova sessão) lê "Anthropic é o backend real" e assume
  que basta setar a env, vai levar a `NotImplementedError` em runtime.
- **Dependência morta** — `anthropic = "^0.40.0"` (16 MB instalado + transitive deps)
  puxada sem uso.
- **Roadmap comunicado incorretamente** — o pitch comercial ("três hats de LLM plugável")
  vira "dois hats" na prática, e um deles é fake.

## Fix sugerido

Escolher uma das opções e propagar para docs:

**Opção A — Remover a promessa Anthropic e ficar só com local:**
1. Deletar branch `anthropic` do `llm_factory.py` (comentário `-> use LLM_BACKEND=fake or local`).
2. Remover `anthropic` do `pyproject.toml`.
3. Editar CLAUDE.md linha 33 → "OpenAI-compatible local server (llama-server)".
4. Editar architecture.md linha 119 → "`Local*` (Sprint 7, real via OpenAI-compatible API)".
5. Editar `.env.example:5` — remover `ANTHROPIC_API_KEY`.

**Opção B — Implementar Anthropic real:**
Criar `core/llm_anthropic.py` espelhando `core/llm_local.py` mas usando `anthropic.Anthropic()`
+ `messages.create(..., tools=[...])` com o schema tool_use gerado por
`EntitySchema.to_llm_schema()`. Bater no factory. Ajustar retry via `tenacity` (que já está
no pyproject).

A opção A é mais honesta com o estado atual (localhost:8080 com Qwen2.5 já cumpre o
objetivo do "LLM real"); opção B mantém a promessa original mas exige ~200 LOC + testes.

## Referências

- `CLAUDE.md` linha 33 e 25.
- `docs/architecture.md` linha 119.
- `.env.example` linha 5.
