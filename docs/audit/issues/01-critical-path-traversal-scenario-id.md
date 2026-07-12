# Path traversal em `scenario_id`, `branch_id`, `entity_id`

**Severity:** Critical
**Priority:** P0 (agora, antes de qualquer deploy público)
**Category:** Security
**Source:** `core/scenario.py:74-81`, `core/snapshot.py:54-58`, `api/main.py:236-346`

## Descrição

`EventLog._dir()` monta o caminho do cenário concatenando `base_dir / scenario_id` sem
nenhuma validação:

```python
# core/scenario.py:73-81
def _dir(self, scenario_id: str) -> Path:
    return self.base / scenario_id

def _events_path(self, scenario_id: str) -> Path:
    return self._dir(scenario_id) / "events.jsonl"

def _manifest_path(self, scenario_id: str) -> Path:
    return self._dir(scenario_id) / "manifest.json"
```

Todos os endpoints FastAPI expõem `scenario_id` como path parameter e passam a string direta
para `EventLog`. Ex.: `GET /scenarios/{scenario_id}` (`api/main.py:236`), `POST /scenarios`
(create com `id=uuid.uuid4().hex[:12]` que é seguro), **mas também** um `POST /scenarios`
que aceita ID fornecido pelo cliente via `CreateScenarioRequest` (embora hoje o `create`
gere UUID, `init_scenario` aceita qualquer id — e uma chamada direta ao módulo passa).

Situações concretas:

1. `GET /scenarios/..%2F..%2Fetc/passwd` — FastAPI decodifica `%2F` para `/` e o path
   resultante em disk é `SCENARIOS_DIR/../../etc/passwd`. Em `SnapshotStore.load()` o path
   é `SCENARIOS_DIR/../../etc/passwd/snapshots/{branch}-seq-{N}.json.zst` — leitura de
   arquivo arbitrário se existir a estrutura esperada.
2. Idem para `entity_id` em `PATCH /scenarios/{sid}/entities/{entity_id}` — vai como
   `Event.target`, que depois é gravado em JSONL (sem ler arquivos de disk direto, mas
   contamina o event log com dados controlados).
3. `Branch.create(scenario_id, parent_seq, name)` usa `name` diretamente como `branch_id`
   (`core/branching.py:57`). `branch_id` vira parte do filename do snapshot
   (`f"{branch_id}-seq-{at_seq}.json.zst"` em `snapshot.py:58`) — um branch chamado
   `"../bootstrap"` cria `SCENARIOS_DIR/<sid>/snapshots/../bootstrap-seq-5.json.zst`,
   escapando `snapshots/`.

## Risco

**Deploy alvo é Fly.io com volume montado em `/data`** (fly.toml). Um atacante com acesso
HTTP (a API está com `allow_origins=["*"]` e sem autenticação — ver finding #03) pode:

- Ler qualquer `manifest.json` / `events.jsonl` acessível ao processo (root do container).
- Escrever/sobrescrever arquivos dentro de `/data` (e possivelmente fora, dependendo do
  syscall — `Path("/data/scenarios") / "../../root/.ssh"` resolve para `/root/.ssh`).
- No dev local (Windows): escrever em `D:/Documents/projects/claude.docker-RAG/` ou acima.

Um cenário chamado `..` seria criado como pasta em `SCENARIOS_DIR/..` (o próprio pai da
pasta de cenários) — cria `manifest.json` e `events.jsonl` no root do projeto.

Note que `scenario_id` também é usado como namespace de cache Redis (`SimCache.__init__`
`key_prefix=scenario_id`). Um cliente que consegue escolher seu `scenario_id` pode injetar
`:` no prefixo e colidir com chaves de outros namespaces (secundário, mas relevante).

## Fix sugerido

Adicionar validação centralizada em `EventLog` e `SnapshotStore`:

```python
import re
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

def _validate_id(id_: str, label: str) -> None:
    if not _SAFE_ID.match(id_):
        raise ValueError(f"invalid {label}: must match {_SAFE_ID.pattern}")

def _dir(self, scenario_id: str) -> Path:
    _validate_id(scenario_id, "scenario_id")
    return self.base / scenario_id
```

E validar todo path que vai a disk também com `Path.resolve()` + `is_relative_to(base)`:

```python
def _dir(self, scenario_id: str) -> Path:
    _validate_id(scenario_id, "scenario_id")
    p = (self.base / scenario_id).resolve()
    if not p.is_relative_to(self.base.resolve()):
        raise ValueError(f"path escapes base: {scenario_id!r}")
    return p
```

Aplicar o mesmo para `branch_id` (usado como nome de arquivo em `SnapshotStore._path`) e
`entity_id` (que vira `Event.target`). No `api/main.py`, adicionar `Depends(...)` que
valida o path parameter antes de bater no core.

## Referências

- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- CWE-22: https://cwe.mitre.org/data/definitions/22.html
