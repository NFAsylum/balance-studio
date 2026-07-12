# Performance — Balance Studio

Números medidos no devbox (RTX 3090 host, Python 3.11, single-thread salvo indicado).
Guardados por `tests/test_performance.py` — o teste falha só em regressão catastrófica
(thresholds = metas da DoD, com folga de ~1000x sobre o medido).

## Simulação

| Cenário | Matches | Medido | Meta (DoD) | Folga |
|---|---:|---:|---:|---:|
| Creature gauntlet (100 × 10) | 1000 | **0,030 s** | < 30 s | ~1000× |
| Creature gauntlet quick (100 × 1) | 100 | **0,004 s** | < 2 s | ~500× |
| Card 500-pool, matches amostrados | 1000 | **0,060 s** | < 60 s | ~1000× |
| Cache hit (repeat, 190 matchups) | 190 (reuso) | **< 5 ms** | < 100 ms | ~20× |

## Tier list emergente (verificação final Sprint 4)

`gauntlet(100 creatures, n_battles=10)` → 1000 battles em 0,030 s → `TierEmergence`
distribui em S/A/B/C/D (20 cada, por quantil de winrate). `DominanceIndex` (top-5%) ≈ 0,10;
`UsageCoverage` = 100/100 creatures em ≥1 match. A tier list **emerge da simulação**, não é
atribuída — é o sinal objetivo (LLM-free) que sustenta a credibilidade do framework.

## Paralelismo

`core/parallel_runner.run_matches_parallel` distribui matches num `ThreadPoolExecutor`
(ordem preservada, resultado idêntico ao serial). Como os simuladores são CPU-bound em
Python puro, o GIL faz o ganho de wall-clock ser ~nulo hoje — e não é necessário, já que o
single-thread bate as metas por ~1000×. O valor é a costura: trocar `ThreadPoolExecutor` por
`ProcessPoolExecutor` no mesmo ponto dá paralelismo real se um simulador mais pesado precisar.

## Cache incremental

`IncrementalSimRunner` cacheia por matchup (`core/sim_cache.py`). Editar 1 entidade invalida
só os matchups que a envolvem (`SimCache.invalidate_touching`); o resto é reusado. Freshness
rastreia só eventos de entidade (create/edit/delete) — simulate/judge não invalidam o cache.
