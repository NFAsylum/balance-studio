# Experiments — Balance Studio

Log de tuning e validação do LLM. Backend: **LLM local** (Qwen2.5-Coder-7B-Instruct Q4_K_M
via llama-server, OpenAI-compatible, ~100 tok/s, GPU). Custo: **zero** (local, ilimitado).

## B6.5 — Validação real dos hats locais (2026-07-11)

Rodado via `LLM_BACKEND=local poetry run python -m scripts.experiment_b6`. Success rate =
fração de entidades **geradas** que passam schema + constraints (3 trials por domain).
Loops = design → simulate → judge → iterate via `IterationEngine.auto_loop(max_steps=3)`.

| Domain | Success (válidas/emitidas) | Target (7B) | Loops | Convergência | Latência design |
|---|---:|---:|---:|---|---:|
| card_game | **15/15 = 100%** | >65% | 2 | ambos convergiram (4 steps, ~10s) | ~9–20 s |
| creature_rpg | **18/18 = 100%** | >55% | 2 | ambos convergiram (4 steps, ~24–36 s) | ~11 s |

**Ambos os targets batidos com folga.** 33 entidades geradas no total, 33 válidas.

### Iterações de prompt (o que importou)

1. **Parsing robusto foi a intervenção decisiva.** O Qwen 7B embrulha a saída em
   ` ```json … ``` ` e adiciona prosa **mesmo com `response_format={"type":"json_object"}`**.
   Sem tratar isso, o Judge quebrava no `json.loads` e o Designer gerava 0. Solução em
   `core.llm_local._parse_json`: tira fences e extrai o primeiro bloco JSON balanceado.
2. **Schema explícito no prompt do Designer** (via `EntitySchema.to_llm_schema()`) — com o
   JSON Schema completo de um item, o modelo acerta tipos e ranges de primeira. Não foi
   preciso few-shot.
3. **Não houve não-convergência de prompt** (a regra dos "3 iterations" não disparou). O
   único ajuste real foi robustez de output, não engenharia de prompt fina.

### Observações de qualidade

- **Judge discrimina bem** (contra a preocupação de scores presos em 0.4–0.6): no smoke,
  `variety` deu **0.30** pra 3 cards parecidos do seed, com rationale coerente ("similar in
  role and ability kind, only slight differences"). **Não precisa do modelo 35B** por ora.
- **Convergência** = `auto_loop` parou quando `iterate` aplicou 0 modificações (dentro dos
  4 steps: design+simulate+judge+iterate). A engine agora **valida o payload de cada
  modification** do iterator e rejeita as inválidas (`rejected_invalid`) — defesa contra o
  7B propor edits malformados; nunca commita estado inválido.
- **Latência**: design 9–20 s (n=5–6), loop completo 10–36 s. Aceitável pro fluxo dev.

### Reprodução

```bash
LLM_BACKEND=local LOCAL_LLM_URL=http://192.168.3.92:8080/v1 \
  poetry run python -m scripts.experiment_b6
```
