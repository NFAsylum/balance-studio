# Balance Studio v2 — Rule-Authoring Meta-Engine (γ)

**Status:** STANDBY desde 2026-07-13
**Decisão original:** Marco optou por manter Balance v1 (arquitetura atual) por conflito com prazo de Babel (TCC) + payback pessoal não fecha em uso solo. γ documentado aqui para revisita futura se contexto mudar.

**Sessão que originou este doc:** conversa longa com Claude Opus 4.7 em 2026-07-13, incluindo ultrathink sobre requisitos técnicos, velocity, riscos e economia do pivô.

---

## O pivô

**De:** sims fixos + LLM ajusta entidades dentro deles (Balance v1 = α).
**Para:** usuário co-autora regras da sim com LLM assistindo; engine determinística interpreta regras user-authored (Balance v2 = γ).

## Visão do produto

Balance γ = **plataforma de rule-authoring assistida por LLM** pra prototipagem de sistemas de jogo. Usuário monta seu jogo via blocos visuais (Blockly) com escape hatch pra Python. LLM assiste autoria, debugging e análise de balance. Sim engine determinística + Monte Carlo overlay cobre 4 domínios.

**Pitch:** *"Você descreve seu jogo em blocos visuais, LLM te ajuda a preencher lacunas, sim engine roda milhares de matches em segundos, você vê onde está desbalanceado antes de gastar tempo em playtest com humanos."*

## Landscape competitivo

| Ferramenta | Foco | LLM assist | Gap que γ preenche |
|---|---|---|---|
| **Machinations** | Economia/loops via node graph | ❌ | Combate tático, targeting, decisões de deck |
| **Ludii** (Maastricht) | Jogos clássicos via Game Description Language formal | ❌ | CCGs modernos, deckbuilders, RPGs de combate |
| **Balance γ** | Rule authoring assistida por LLM pra jogos modernos | ✅ | Categoria nova |

γ ocupa a clareira entre economia (Machinations) e clássicos formais (Ludii), com IA-assist como diferencial.

## Arquitetura (12 componentes)

### 1. Rule Engine Core
Interpretador de regras. ECS + event bus + tick determinístico com RNG seeded. Rules-as-data (JSON/DSL). Event-driven (on_play, on_death) + phase-based (upkeep, main, combat, end).
**~500-800 LOC** de core bem escrito.

### 2. Rule DSL + Interpretador
Linguagem que os blocos compilam pra. Verbos de domínio (`draw_card`, `deal_damage`, `spawn_entity`, `gain_resource`, `move_to_zone`, `count_matching`), control flow (`if/else`, `foreach`, `sequence`), selectors (`self`, `random_target`, `all_matching(tag=X)`), triggers.
Serialização JSON. Validação estática (loops infinitos, refs inválidas).
**~600-1000 LOC.**

### 3. Blockly Integration
Editor visual de rules. Google Blockly com customização heavy pra blocos game-specific.
Blocos por domínio: 30-50 (triggers + actions + conditions + selectors + control flow).
**~60-100h.** Blockly tem learning curve mas é o único caminho que escala.

### 4. Escape Hatch Python
Programador escreve função Python em `blocks/custom/`; type hints geram signature do bloco na UI. Sandbox obrigatório se algum dia deploy pra outros.
**~40-60h.**

### 5. State Model Universal
- **Entities**: id + tags + components dict
- **Zones**: deck/hand/field/graveyard/exile (card game), party/backup/defeated (creature RPG), backlog/in_progress/launched (product mgmt), pool/assigned/on_leave (team comp)
- **Resources**: named counters por player (mana, life, energy, budget, hours, XP)
- **Turn structure**: number + active_player + phase + priority_player
- **RNG state**: seed-based, deterministic

**~100-150 LOC universal + 30-50 LOC/domínio.**

### 6. Sim Runner
Multi-run paralelo, métricas plugáveis, timeout de rules (aborta loop infinito), event log per sim.
Baseia no `sim_cache.py` atual (~300 LOC). Refactor: **~150-200h.**

### 7. LLM Integration Refactor
Novos usos:
- **(a) Rule authoring assist**: usuário escreve NL → LLM propõe blocos → UI força inspeção antes de commit
- **(b) Debugging**: sim crashou → LLM lê rule que triggerou + traceback → sugere fix
- **(c) Análise de balance**: recebe rules do usuário como contexto, não só entities
- **(d) Test case generation**: sugere edge cases, roda sim automatizado, mostra outliers

**~80-120h** de refactor + prompts novos.

### 8-10. Domínios refeitos
- **card_game** (70-85% fidelity de CCG típico): zones + mana + fases + rules pre-shipped. **~40-60h.**
- **creature_rpg** (70-85% de Pokemon/JRPG): party + HP/MP + type effectiveness. **~40-60h.**
- **team_composition** (50-70% de workflow real): repensado. Value é pra staffing acadêmico/consultoria — manager real prefere intuição. **~30-40h.**

### 11. product_management from scratch
- **A arquitetura de rule engine range aqui**: PM real exige Monte Carlo sobre distribuições de effort/impact + agentes adversariais (competidor).
- **Compromisso viável**: Monte Carlo overlay + stochastic rules pro competitor. Fidelity 40-60%.
- **Utilidade real**: "invisto X horas em feature Y ou Z, qual dá melhor range de ROI" — **se** usuário souber estimar distribuições. Se estimativa é ruim, sim mente com precisão.
- **~40-60h + design pesado.**

### 12. Testing suite + docs + tutorial
- **Testing suite (não-negociável)**: property-based (Hypothesis), golden tests, fuzzing. Rule engine bugs são silenciosos — sem essa cobertura γ vira "sim que cospe número lindo mas errado". **~80-120h.**
- **Docs + tutorial interativo**: reference de blocos + guided tour "crie sua primeira carta em 5 min". **~40-60h.**
- **UI workspace** (Cursor-style): parte da visão A original, aqui expandida pra ter painel de rules. **~60-100h.**

## Effort total

| Componente | Horas |
|---|---|
| Rule engine core | 40-80h |
| Rule DSL + interpretador | 50-80h |
| Blockly integration | 60-100h |
| Python escape hatch + sandbox | 40-60h |
| State model | 30-50h |
| Sim runner refactor | 30-50h |
| LLM integration refactor | 80-120h |
| Domain: card_game refeito | 40-60h |
| Domain: creature_rpg refeito | 40-60h |
| Domain: team_composition repensado | 30-40h |
| Domain: product_management from scratch | 40-60h |
| Testing suite | 80-120h |
| Docs + tutorial | 40-60h |
| UI workspace | 60-100h |
| **Total** | **660-1040h** |

**Estimativa central:** ~850h.

**Cortes viáveis pra v1 mínimo (~500h):**
- Só card_game + creature_rpg no início (product_mgmt vira v1.5, team_comp diferido)
- Tutorial minimalista
- Testing só do core (sem fuzzing)
- Blockly com ~30 blocos em vez de 50

**Não cortar:** rule engine core, testing do core, state model, DSL. Fundação errada = retrabalho catastrófico.

## Timeline projetado

Baseado em velocity observada de Storyteller+Balance: ~8-15h Claude output por 1h supervisão Marco.

- **Supervisão total necessária:** ~150h Marco
- **Aggressive** (4h/dia útil, 6 dias/semana): γ v1 em **6-10 semanas**
- **Sustentável** (2h/dia, 5 dias/semana): γ v1 em **12-20 semanas**
- **Fim-de-semana warrior** (10-15h/semana): γ v1 em **20-40 semanas**

**Modelo de 2 instances:** 1 lead full-time em γ + 1 maintenance (Storyteller bugfix + review independente). γ **não é paralelizável internamente** — interdependências arquiteturais fortes (rule engine ↔ DSL ↔ blocks ↔ state model).

## Riscos

**Técnicos:**
- **Silent engine bugs**: sim produz número errado, você não sabe. Mitigação: testing suite pesada.
- **DSL ossificação**: v1 sai, usuários authoram — mudar semântica quebra tudo. Design com migration em mente desde o dia 1.
- **Blockly ceiling**: recursão profunda, targeting complexo ficam ilegíveis em blocos. Escape hatch resolve mas fragmenta UX.
- **LLM code generation errante**: LLM propõe rule com bug sutil. UI precisa **forçar inspeção** antes de commit.

**Produto:**
- **Chicken-and-egg de adoção**: sem templates de qualidade, ninguém adota; sem adoption, ninguém authora templates.
- **Comparação injusta**: Ludii tem 15 anos de research; Machinations 12 anos pago. γ v1 vai parecer beta.
- **Nicho pequeno**: 100-1000 usuários lifetime realista com marketing OK. Não é viral.
- **Commoditização**: se OpenAI/Anthropic lançarem "GPT for game design", γ fica genérico.

**Pessoais:**
- **Babel TCC prazo real** — competição direta por tempo. Risco mais material.
- **Perfectionism**: rule engines atraem "só mais um edge case". Ship discipline dura.
- **Post-Max cost**: $200-1000 em Claude API dependendo de otimização. Financiar vale?
- **Sunk cost fallacy**: 200h dentro e Blockly não escala → difícil abandonar.

## Payback analysis

**Solo (Marco só):**
- 5-10 protótipos * 35h saved/proto = 175-350h benefit
- vs 850h invested
- **Loss de ~500h.** Não paga em uso pessoal.

**Comunidade:**
- 100 usuários * 3 protótipos * 35h = 10,500h economizadas coletivamente
- 1000 usuários = 100,000h
- **Paga se adoção acontecer.** Adoção real é incerta.

**Conclusão:** γ paga como projeto de impacto/portfólio, não como time-savings pessoal.

## Gatilhos pra revisitar

Considere γ quando ao menos 3 dos abaixo forem verdade:

1. Balance v1 (α) atingiu >100 usuários com pedidos concretos de "quero authorar meu próprio sim"
2. Babel TCC completado e defendido
3. Marco tem 3-6 meses de runway (tempo + energia + $) alocáveis
4. Marco identificou game framework como direção de carreira (ex: quer virar Ludii-modern-day founder)
5. LLM code generation reliability melhorou significativamente (menos revisão manual necessária)
6. Anthropic/OpenAI **não** lançaram produto que ocupe esse espaço

Se apenas 1-2 forem verdade: continue com Balance v1 α e revisite depois.

## Alternativas descartadas

- **β (deepen sims genericamente sem rule authoring)**: paga custo alto sem entregar utilidade real (continua sem bater jogo específico). Pior dos mundos.
- **C-saída (share/fork via URL)**: só faz sentido se Balance for deployado público. Local não usa. Diferido junto com γ.

## Referências

- Machinations: https://machinations.io/
- Ludii: https://ludii.games/
- Blockly: https://developers.google.com/blockly
- Discussão original de β/γ: sessão de 2026-07-13 (esta)
- Balance v1 (α) roadmap: quando escrito, virá em `docs/inbox-archive/YYYY-MM-DD-workspace-v1.md`
