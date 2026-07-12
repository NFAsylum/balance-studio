# `sqlalchemy`, `alembic`, `tiktoken` no `pyproject.toml` mas nunca usados

**Severity:** Low
**Priority:** P3
**Category:** Code-guidelines
**Source:** `pyproject.toml:14-24`

## Descrição

```toml
# pyproject.toml
sqlalchemy = "^2.0.0"
alembic = "^1.13.0"
...
tiktoken = "^0.8.0"
```

`grep -rn "sqlalchemy\|alembic" core/ api/ domains/` retorna zero. `tiktoken` idem.
O `deploy/README.md:76-78` já reconhece:

> **Sem camada SQL.** A persistência é file-based (event log + snapshots no volume `/data`).
> `DATABASE_URL` e os deps `sqlalchemy`/`alembic` são vestigiais do plano pré-pivot — não
> há migração Postgres a rodar. Remover os deps é uma limpeza opcional.

`tiktoken` (contador de tokens Anthropic/OpenAI) faz sentido para uso de LLM real, mas o
código não conta tokens em lugar nenhum (`grep -rn "tiktoken" .` só bate no lock file).

## Risco

- **Bloat de imagem Docker:** sqlalchemy ~ 6 MB, alembic ~ 4 MB, tiktoken ~ 15 MB (com wheel
  binário C extension). Aumenta cold start no Fly.io e tamanho do container.
- **Superfície de CVE inflada:** cada dep é um vetor. Não use deps que não usa.
- **Confusão sobre a arquitetura:** um novo dev que abre o pyproject pensa "ah, tem SQL"
  e vai procurar. Não encontra. Frustrante e enganoso.

`redis = "^8.0.1"` e `openai = "^2.45.0"` são usados de fato (via `RedisCacheBackend` e
`LocalDesigner`), então esses ficam.

`anthropic = "^0.40.0"` cabe em finding #05 — não usado, mas o gap é mais crítico lá.

## Fix sugerido

```bash
poetry remove sqlalchemy alembic tiktoken
poetry lock
```

Editar CLAUDE.md linha 32 removendo "SQLite (experimentos, dev)" e substituindo por "file
system (event log + snapshots)". Editar `.env.example` removendo `DATABASE_URL`.

## Referências

- Nenhuma. É housekeeping.
