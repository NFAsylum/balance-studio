#!/usr/bin/env bash
# Bootstrap do projeto Balance Studio. Roda uma vez pra criar estrutura.
# Uso: bash bootstrap.sh

set -euo pipefail

echo "==> Setting up Balance Studio project structure"

# Criar pastas
mkdir -p core/metrics core/prompts
mkdir -p domains/card_game domains/creature_rpg domains/team_composition
mkdir -p api tests scripts configs deploy
mkdir -p docs
mkdir -p ui

# __init__.py
touch core/__init__.py core/metrics/__init__.py
touch domains/__init__.py
for d in card_game creature_rpg team_composition; do
  touch "domains/$d/__init__.py"
done
touch api/__init__.py tests/__init__.py

# pyproject.toml
if [ ! -f pyproject.toml ]; then
cat > pyproject.toml <<'EOF'
[tool.poetry]
name = "balance-studio"
version = "0.1.0"
description = "Generic LLM-powered balance testing framework with domain plugins"
authors = ["marco <marcooinotna13@outlook.com>"]
readme = "README.md"
packages = [{include = "core"}, {include = "domains"}, {include = "api"}]

[tool.poetry.dependencies]
python = "^3.11"
anthropic = "^0.40.0"
fastapi = "^0.115.0"
uvicorn = "^0.32.0"
sqlalchemy = "^2.0.0"
alembic = "^1.13.0"
pydantic = "^2.9.0"
pydantic-settings = "^2.5.0"
diskcache = "^5.6.0"
zstandard = "^0.23.0"
python-dotenv = "^1.0.0"
tenacity = "^9.0.0"
tiktoken = "^0.8.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-cov = "^5.0.0"
pytest-mock = "^3.14.0"
ruff = "^0.7.0"
mypy = "^1.13.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
EOF
echo "==> pyproject.toml created"
fi

# .env.example — SQLite + diskcache pro dev; Postgres + Redis na prod (Sprint 7)
if [ ! -f .env.example ]; then
cat > .env.example <<'EOF'
ANTHROPIC_API_KEY=sk-ant-...
# SQLite local pro dev. Prod migra pra Postgres via Fly (Sprint 7).
DATABASE_URL=sqlite:///./balance_studio.db
# Diretório do diskcache. Prod usa Redis (Sprint 7).
CACHE_DIR=./.diskcache
LOG_LEVEL=INFO
LLM_MODEL=claude-sonnet-4-6
EOF
echo "==> .env.example created"
fi

# .gitignore
if [ ! -f .gitignore ]; then
cat > .gitignore <<'EOF'
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
.venv/
.env
*.egg-info/
.mypy_cache/
.ruff_cache/
.DS_Store
# Frontend
node_modules/
.next/
out/
dist/
.turbo/
EOF
echo "==> .gitignore created"
fi

# README stub
if [ ! -f README.md ]; then
cat > README.md <<'EOF'
# Balance Studio

Generic LLM-powered balance testing framework. Domains plug in via a small interface; the core provides schema, generation, simulation, metrics, and UI.

Domains included: card game, creature RPG, team composition.

Status: in progress. See `docs/tasks.md`.
EOF
fi

# UI: placeholder (Next.js será criado no Sprint 4 via `pnpm create next-app`)
if [ ! -f ui/README.md ]; then
cat > ui/README.md <<'EOF'
# UI

Frontend Next.js criado no Sprint 4. Não iniciar até core+card game estarem prontos.
Comando quando chegar a hora: `pnpm create next-app ui --typescript --tailwind --app --src-dir --import-alias "@/*"`
EOF
fi

# Git init
if [ ! -d .git ]; then
  git init
  git branch -M main
  git add .
  git config user.name "NFAsylum"
  git config user.email "marcooinotna13@outlook.com"
  git commit -m "chore: bootstrap Balance Studio project structure"
  echo "==> Git initialized with first commit"
fi

echo ""
echo "==> Done. Next steps:"
echo "    1. Copy .env.example to .env and fill ANTHROPIC_API_KEY"
echo "    2. poetry install"
echo "    3. Start Sprint 1: read docs/tasks.md"
