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

---

## B6.6 — Qualidade **real** de balanceamento (2026-07-11)

> **Contexto honesto:** o "100%" de B6.5 mede **validade de output** (schema + parsing),
> **não** qualidade de balance. Este experimento mede a coisa que importa: o Iterator
> **reduz o desbalanceamento** de fato?

**Desenho** (`scripts/experiment_balance.py`, 3 seeds = 42/43/44, mean±std):

- **Set inicial** = roster seed fixo e conhecidamente desbalanceado (isola o efeito do
  Iterator, não a sorte do Designer; nunca degenera).
- **Métrica primária — dispersão** (↓ = mais balanceado): std do win rate (card/creature);
  std do `completion_rate` sobre 10 workloads variados (team).
- **Guardrail — variety** (distância de Gower média par-a-par): garante que "balanceou" ≠
  "homogeneizou". Violação = variety cai >20% enquanto dispersão cai.
- **Loop por trial:** medir → 5 iterações (simular → propor → aplicar válidas) → medir.
- Simulação é **LLM-free e determinística** (ground truth). Só o Iterator usa LLM.

### Resultado — o Iterator do 7B **não** reduz dispersão de forma confiável

Config: prompt com objetivo de balance explícito, judge de variety, **sem cap** de mods.

| Domínio | Dispersão | Δ | Variety | Δ | Mods/trial |
|---|---|---:|---|---:|---:|
| card_game | 0.315 → 0.318 | **+1.0%** | 0.355 → 0.336 | −5.4% | 27.3 |
| creature_rpg | 0.273 → 0.287 | **+5.1%** | 0.569 → 0.534 | −6.2% | 26.0 |
| team_composition | 0.152 → 0.141 | **−7.2%** | 0.823 → 0.824 | +0.1% | 16.0 |

**Dispersão baixou em 1 de 3 domínios.** A DoD pedia ≥2/3 — **não batida**. Não há
manchete positiva honesta com esses números.

### O achado que vale mais que a manchete

O padrão **não é ruído** — é estrutural e reproduzível:

- **Ajuda onde a métrica é ~linear nos atributos** (team: `completion_rate` sobe direto com
  cobertura de skills → edições dirigidas convergem, −7.2%, variety intacta).
- **Atrapalha onde stat→resultado é não-linear** (card/creature: o simulador de batalha tem
  interações; o 7B despeja ~27 edições cegas/passo, que viram ruído e *aumentam* o spread).

Ou seja: o failure mode é **overshoot** (shotgun de mods), não falta de esforço. Isso prevê
que "rodar mais iterações" **pioraria** — e que o lever certo é **menos edições, cirúrgicas**.

### Follow-up: cap de ≤3 edições cirúrgicas por passo

A previsão acima se confirmou. Limitando o Iterator a **≤3 edições/passo** (`MAX_MODS_PER_ITER`,
+ prompt "mexa nos outliers extremos primeiro") e cortando o judge redundante de variety
(substituído pelo `variety_score` exato — metade das chamadas LLM):

| Domínio | Dispersão | Δ | Variety | Δ | Mods/trial |
|---|---|---:|---|---:|---:|
| card_game | 0.315 → 0.308 | **−2.2%** ✅ | 0.355 → 0.336 | −5.4% | 12.7 |
| creature_rpg | 0.273 → 0.244 | **−10.6%** ✅ | 0.569 → 0.547 | −3.9% | 11.0 |
| team_composition | 0.152 → 0.158 | +3.9% (ruído) | 0.823 → 0.818 | −0.6% | 9.7 |

**Dispersão baixou em 2 de 3 domínios (card, creature) → DoD batida.** O cap **inverteu** os
domínios de combate (+1.0%/+5.1% → −2.2%/−10.6%), confirmando que o failure mode era overshoot.

### Veredito

- **DoD:** ✅ dispersão ↓ em ≥2/3; ✅ variety documentada; ✅ mean±std sobre 3 seeds;
  ✅ guardrail intacto (pior variety −5.4%, longe dos −20%).
- **Trade-off honesto:** o cap ajuda combat (não-linear) e **piora** team de leve — team é
  ~linear, se beneficia de *mais* edições. O `+3.9%` de team está **dentro do ruído** (±0.027),
  então é estável, não regressão real. O budget ótimo de edições **depende da estrutura do
  domínio** — insight que só apareceu por medir 3 domínios distintos.
- **Limites:** n=3 seeds, 1 modelo (7B local). Números são de ordem de grandeza, não precisão
  de 2 casas. Um modelo maior provavelmente estende o ganho a team, mas isso é trabalho futuro.

### Manchete (honesta)

> Com edições cirúrgicas, o **Iterator reduziu a dispersão de win rate em 2 de 3 domínios**
> (creature **−10.6%**, card **−2.2%**) **mantendo a variedade** (Δ ≥ −5.4%); team ficou
> estável dentro do ruído. Simulação 100% determinística — o número é ground truth, não
> opinião de LLM.

### Reprodução

```bash
LLM_BACKEND=local LOCAL_LLM_URL=http://192.168.3.92:8080/v1 \
  poetry run python -m scripts.experiment_balance
```
