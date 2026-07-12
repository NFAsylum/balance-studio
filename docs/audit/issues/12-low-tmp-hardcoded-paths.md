# `/tmp/…` hardcoded em scripts de experimento (quebra no Windows)

**Severity:** Low
**Priority:** P2
**Category:** Testing
**Source:** `scripts/experiment_balance.py:155`, `scripts/experiment_b6.py:23`

## Descrição

```python
# scripts/experiment_balance.py:155
_OUT = "/tmp/exp_balance_result.json"

# scripts/experiment_b6.py:23
_BASE = Path("/tmp/claude-1000/-workspace/7e6a8d11-9409-4f9a-b36d-8c76ac447255/scratchpad/exp_b6")
```

O segundo é obviamente um caminho de sandbox de uma sessão Claude anterior (o UUID
`7e6a8d11-...` é specific). Nada semanticamente meaningful — só sobreviveu ao commit.

Ambos quebram em Windows (`OSError: [Errno 22] Invalid argument: '/tmp/...'`) e em qualquer
Linux com política restritiva de /tmp.

## Risco

- **Desenvolvedor Windows não consegue rodar os experimentos** — o próprio dev humano
  (marco) que criou o projeto usa Windows (working dir `D:/Documents/...`). Reproduzir os
  números do README (que vieram de experiment_balance.py) fica impossível localmente sem
  editar o script.
- **`experiment_b6.py` provavelmente nunca roda pra ninguém** — o caminho é sandbox
  específico, não existe fora daquela sessão.
- **Cheirinho de dev sujo:** artefatos de sessão de LLM commitados ao repo.

## Fix sugerido

```python
# ambos scripts
import tempfile
from pathlib import Path

_OUT = Path(tempfile.gettempdir()) / "exp_balance_result.json"
```

Ou usar `os.path.join(os.path.expanduser("~"), ".balance-studio", "experiments", ...)`.

Para `experiment_b6.py`, o UUID hardcoded deve ser removido: substituir por
`Path("./scratchpad/exp_b6")` (relativo ao repo, já ignorado pelo `.gitignore` via
`.diskcache/` — precisa adicionar `scratchpad/` ao .gitignore também).

## Referências

- `tempfile.gettempdir()` funciona em Win/Linux/Mac.
