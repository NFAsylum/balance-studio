> **Note:** This document discusses design considerations that reference commercial games by name for comparative and structural purposes. See README `## Legal` section for full non-affiliation disclosure.

# Product Audit — Balance Studio (2026-07-12)

Inventário completo do que separa o estado atual de um **produto usável por usuário real**.

Legenda:
- **S** = Severity: `C`ritical (produto quebrado), `H`igh (funciona mas frustrante), `M`edium (evitável), `L`ow (nice-to-have)
- **P** = Priority: P0 (agora), P1 (próximo), P2 (depois), P3 (backlog)
- **E** = Effort estimado em horas

Total: **~35 issues, ~65-90h pra produto usável.**

---

## 1. Qualidade de conteúdo LLM (prompts não tunados)

### 1.1 [C, P0, 1h] Nomes de entidade genéricos ("Carta-0", "Entidade-1")
`core/llm_local.py::LocalDesigner.design()` — system prompt otimiza validação, não criatividade. Não instrui LLM a criar nomes temáticos.
**Fix:** adicionar ao system prompt: *"Give each entity a distinctive, thematic name that reflects the brief. Names must read as real entities from the setting (not placeholders like 'Card-1' or 'Entity-A'). Same for descriptions if the field exists — write flavor text, not placeholder."*

### 1.2 [C, P0, 30min] Campos opcionais ignorados (skills vazias em creatures)
LLM omite campos que percebe como "extras" (skills, resistances). `to_llm_schema()` provavelmente não marca fields como `required`, e prompt não enforça completude.
**Fix:** (a) marcar todos os fields do EntitySchema como `required` no JSON Schema output. (b) adicionar ao prompt: *"Every field defined in the schema must be present in every entity. No omissions."*

### 1.3 [H, P1, 2h] Prompts sem few-shot examples
Designer/Judge/Iterator sem exemplos do que é "bom output". Modelo 7B precisa de guidance forte.
**Fix:** adicionar 2-3 few-shot examples por prompt (input → output ideal), extraídos dos seeds.

### 1.4 [H, P1, 3h] Iterator propõe mudanças mecanicamente sem racional narrativo
Justificativas do Iterator são secas ("increase hp"). Não explica *por quê* aquela mudança serve o objetivo específico.
**Fix:** prompt do Iterator inclui reflexão passo-a-passo — "identify the outlier, explain why it's outlier, propose targeted fix, explain why the fix addresses the specific metric".

### 1.5 [M, P1, 2h] Judge dá scores sem discriminação em escala pequena
Judge tende a devolver scores em faixa estreita (0.4-0.6). Modelo 7B tem baixa discriminação subjetiva.
**Fix:** rubricar o prompt do Judge — "0.0 = terrible (concrete criteria), 0.5 = average, 1.0 = exceptional (concrete criteria)".

---

## 2. Controles de intent do usuário

### 2.1 [C, P0, 6h] Sliders/controles pra Designer não existem
UI só oferece textarea "brief". Usuário não pode indicar power scale, variety, complexity, theme adherence sem escrever prosa.
**Fix:** adicionar painel "Generation Intent" ao lado do brief com sliders:
- Power scale (weak / average / strong)
- Variety (uniform / distinct / experimental)
- Complexity (simple / moderate / rich)
- Theme adherence (loose / balanced / strict)
Cada slider vira modificador no prompt.

### 2.2 [C, P0, 4h] Sem preview antes de gerar
Usuário clica "generate", espera 30-90s, vê resultado. Se não gostar, refaz do zero.
**Fix:** botão "Preview 1 entity" gera exemplo isolado antes de comprometer os N. Ou stream do primeiro resultado.

### 2.3 [H, P1, 3h] Sem controle de granularidade do Iterator
Iterator pode fazer 1-27 mudanças por passo. Sem controle do usuário.
**Fix:** slider "Aggressiveness: surgical (1-3 changes) / balanced (5-10) / broad (15+)". Já sabemos que "surgical" funciona melhor (achado do B6.6).

### 2.4 [H, P1, 2h] Sem "protect these entities" (lock)
Usuário pode gostar de uma carta e não querer que o Iterator mexa nela. Não existe UI pra isso.
**Fix:** botão "lock" em cada EntityCard. Iterator pula entities locked.

---

## 3. Schema e configuração

### 3.1 [C, P0, 15h] Schema hardcoded no plugin — impossível personalizar
`domains/card_game/schema.py::get_schema()` retorna schema fixo com ranges fixos (HP 1-20). Usuário que quer MTG (Life 20 + creatures P/T variável) ou YuGiOh (LP 8000) precisa criar novo domain em Python.
**Fix:** ver docs de arquitetura — schema deve vir de **plugin_schema + scenario_overrides**. Scenario carrega `manifest.json` com `schema_overrides` que mescla com defaults do plugin. UI expõe editor de schema antes de gerar entidades.

### 3.2 [C, P0, 6h] Sem presets pra famílias populares
Sem "Hearthstone template" ou "MTG template" ou "YuGiOh template" no card_game. Sem "Pokemon-like" ou "Souls-like" no creature_rpg. Usuário começa do zero e pergunta "quais valores são razoáveis?".
**Fix:** cada domain tem `presets/*.json` com 3-5 templates prontos. UI lista no fluxo de criar scenario.

### 3.3 [H, P1, 3h] Sem editor de metrics do usuário
Métricas são fixas do plugin. Se usuário quer "cartas legendárias devem ser <5% do roster", não tem como expressar.
**Fix:** UI de "custom metric" via mini-DSL (ex: `entity.filter(cost=5).count() / total <= 0.05`).

---

## 4. Onboarding / primeiro uso

### 4.1 [C, P0, 4h] Home vazia sem CTA claro
Primeira visita mostra "Nenhum cenário". Nenhum tutorial, nenhum "try example", nenhuma explicação.
**Fix:** hero com 1 parágrafo do produto + botão "Try card game example" que carrega scenario pré-populado + link "Watch 2-min intro video".

### 4.2 [H, P1, 3h] Sem tour guiado nas telas
Usuário criando primeiro scenario não sabe o que timeline, freshness indicators, branches significam.
**Fix:** overlay tipo Intro.js na primeira visita mostrando: "isso é o brief", "isso é o timeline", "isso é o painel de objetivos".

### 4.3 [H, P1, 2h] Empty states secos
"Nenhum branch", "Sem métricas", "Sem eventos" — texto cinza sem ilustração ou CTA.
**Fix:** cada empty state ganha ícone + microcopy amigável + botão de ação relevante.

### 4.4 [M, P2, 2h] Sem exemplos in-context
Painel de brief não mostra exemplos de briefs bem-escritos.
**Fix:** ao lado do textarea, botão "See examples" mostra 5 briefs modelo por domain.

---

## 5. Feedback e status

### 5.1 [C, P0, 3h] Sem indicador de progresso durante LLM operations
Design de 5 cartas leva 30-90s. Usuário vê spinner genérico ou nada, sem noção de quanto falta.
**Fix:** SSE do backend empurra progress ("Generating card 3 of 5..."). Ou skeleton de N cards que vão populando conforme LLM responde.

### 5.2 [H, P1, 2h] Iterator sem indicação de "por que essa mudança"
Timeline mostra "edit_entity: Card-3" mas não o **motivo**. Reasoning existe no evento mas não é destacado.
**Fix:** cada evento do iterator na timeline mostra card expandável com o reasoning.

### 5.3 [H, P1, 2h] Sem confirmação antes de rodar operação cara
Clique em "Iterate" dispara um loop de 30-90s por passo. Sem "isso vai levar X min, continuar?".
**Fix:** modal de confirmação estimando tempo + custo (mesmo que $0 local) + opção "run in background".

### 5.4 [M, P2, 1h] Sem cancelar operação em curso
Uma vez que Iterator começou 10 passos, sem forma de parar.
**Fix:** botão "Cancel" que envia signal, e limpa parciais.

---

## 6. Erros e recuperação

### 6.1 [C, P0, 3h] llama-server timeout crash UI
Se llama-server demora >180s ou cai, request morre sem retry, UI mostra "Failed to fetch".
**Fix:** timeout configurável, retry automático (2 tentativas), toast claro + botão "retry" em falha final.

### 6.2 [H, P1, 2h] LLM retorna JSON malformado — usuário vê stack trace
Se prompt tuning falha e Local retorna prosa ao invés de JSON, tela quebra.
**Fix:** error boundary com mensagem amigável + botão "regenerate" + link "reportar issue".

### 6.3 [M, P2, 1h] Sem retry inteligente com feedback
Retry atual repete o mesmo prompt. Deveria adicionar o erro no próximo prompt como feedback pro LLM.
**Fix:** já está parcial no Designer. Estender pra Judge e Iterator.

---

## 7. Persistência e ciclo de vida

### 7.1 [C, P0, 4h] Zero export/import
Cenário é fs local no container. Não tem export pra `.zip`/`.json` compartilhável. Não tem import de cenário compartilhado.
**Fix:** botão "Export scenario" empacota `manifest.json` + `events.jsonl` + `snapshots/` num `.tar.gz` (spec original previa isso). Botão "Import" oposto.

### 7.2 [H, P1, 3h] Sem preview antes de deletar scenario
Delete é um clique. Se acidental, perde trabalho de 30-60 min.
**Fix:** confirmação modal + soft delete (fica em lixeira por 30 dias) + "restore" button.

### 7.3 [M, P2, 2h] Sem "clone/duplicate scenario"
Se usuário quer testar variação, precisa criar do zero.
**Fix:** botão "Duplicate" cria cópia com estado atual como ponto zero.

### 7.4 [M, P2, 3h] Sem migration path se schema muda
Se o usuário atualizou o produto e o schema do card_game mudou, cenários antigos quebram sem aviso.
**Fix:** version tag em cada scenario + warning "this scenario uses schema v0.2, current is v0.3" + migration wizard.

---

## 8. UX details

### 8.1 [H, P1, 2h] EntityEditor sem range visível nos campos numéricos
Você bateu no HP > 20 → erro sem contexto. Ranges aceitos não aparecem antes.
**Fix:** label de cada num field mostra `HP (1-20)`. Slider em vez de number input onde há range definido. Placeholder informativo.

### 8.2 [H, P1, 2h] Timeline não distingue actor visualmente
Cores/ícones diferentes por actor (user, llm-designer, llm-judge, llm-iterator) existem mas sutis. Difícil scanear.
**Fix:** cores fortes (user = azul, llm-designer = verde, judge = amber, iterator = purple) + ícone reconhecível.

### 8.3 [M, P2, 3h] Sem search/filter na timeline
Cenário com 100 eventos vira parede de scroll.
**Fix:** search por texto no reasoning, filter por actor, filter por kind, date range.

### 8.4 [M, P2, 3h] Objectives picker complexo demais
Multi-objective + Pareto é conceito difícil. Usuário sem background em otimização não entende.
**Fix:** presets de objectives por domain ("balance winrate 50%", "maximize variety") + explicação inline do que Pareto significa + exemplo visual.

### 8.5 [M, P2, 2h] Sem dark mode
Existe i18n mas cor scheme é fixo.
**Fix:** toggle no header + persistir em localStorage.

### 8.6 [L, P3, 1h] Frontend em Next 15 com "Try Turbopack" ad
Não é sério pra portfólio ver esse nag.
**Fix:** upgrade pra Next 16 (Storyteller já usa).

---

## 9. Documentação / help

### 9.1 [H, P1, 4h] Nada in-product explica o que hats são
Usuário vê botões "Projetar/Simular/Avaliar/Iterar" sem entender que são fases separadas com custos diferentes.
**Fix:** tooltip em cada botão explicando + link pra doc "Understanding the Design → Simulate → Judge → Iterate loop".

### 9.2 [H, P1, 3h] README foca em técnica, não em produto
`README.md` atual é excelente pra dev/recruiter mas usuário final não sabe se ele é o público.
**Fix:** adicionar seção "Are you a game designer?" no topo com use case flow em GIF.

### 9.3 [M, P2, 3h] `writing-a-domain.md` é dev-focused
Fecha porta pra usuário que quer "hacker o produto sem código". Idealmente domains poderiam ser JSON, não Python.
**Fix:** trabalho grande — schema definition em JSON, register via UI. **Marcar como v2.**

### 9.4 [M, P2, 2h] Sem changelog visível
Deploy futuro precisa mostrar "o que mudou".
**Fix:** `CHANGELOG.md` + página `/changelog` na UI.

---

## 11. Diferenciação visual por domain (adicionado pós-feedback)

### 11.1 [C, P0, 10h] Entidades renderizadas como JSON genérico — zero identidade visual
`EntityCard` mostra key:value dos campos. Card game, creature RPG, team composition ficam **idênticos visualmente**. Perde totalmente o "feel" do domínio.
**Fix:** cada domain fornece componente React customizado de render:
- **card_game**: layout de carta — nome no topo com border color por ability_kind, ícone/emoji central (deal_damage=⚔, heal=❤, shield=🛡, draw=🎴), stats no rodapé (HP/Dmg/Cost) em pill boxes
- **creature_rpg**: layout pokédex — sprite/emoji do tipo (fire=🔥, water=💧, plant=🌿) à esquerda, painel de stats à direita, badges de tipo coloridos, resistances como pequenos ícones em linha
- **team_composition**: layout crachá — avatar circular com inicial ou emoji do skill principal, nome + seniority destaque, skills como tags coloridas por categoria
Framework core teoricamente já tem hook pra domain-specific views (`ui/config/domain-views.ts` do plano original). Provavelmente só o fallback genérico foi implementado. Missing: os 3 components + registro.

### 11.2 [H, P1, 4h] Sem iconografia ou paleta por domain
Mesmo com component custom, faltam ícones consistentes. Emoji não é escala.
**Fix:** ícones SVG (Lucide React já disponível) por conceito de domain + paleta específica (card_game = crimson/gold; creature_rpg = forest green; team = business blue).

### 11.3 [M, P2, 3h] Sem preview de renderização no schema editor
Se o usuário customiza schema (ver 3.1), a UI precisa mostrar como fica a entidade renderizada em tempo real.
**Fix:** painel dividido — editor de schema à esquerda, preview de card à direita atualizando.

---

## 10. Deploy pra usuários reais

### 10.1 [C, P0, 6h] LLM local não é acessível de deploy remoto
Fly.io não vê `192.168.3.92`. Deploy público quebra a menos que trocar backend.
**Fix:** implementar `AnthropicDesigner/Judge/Iterator` full (start já feito, ~2h finalizar) OU expor llama-server via tunnel (Tailscale, ngrok) — não escala pra outros usuários.

### 10.2 [H, P1, 3h] Sem multi-user isolation
Todo scenario compartilha namespace de disco. Usuário A vê scenario de usuário B.
**Fix:** namespace por `user_id` em todos os paths (Scenarios/, Sim_cache/). Auth já existe (`BALANCE_API_KEY`), mas é single-tenant.

### 10.3 [H, P1, 2h] Sem limites de recursos
Usuário pode criar 1000 scenarios, cada um com 500 entidades. Sem quota, sem warnings.
**Fix:** limites por conta + progress bar + upgrade path.

### 10.4 [M, P2, 3h] Sem observability
Sem logs estruturados, sem métrica de erro, sem trace de latência.
**Fix:** structured logging + OpenTelemetry export + dashboard mínimo.

---

## Sumário

| Categoria | Issues | Effort |
|---|---:|---:|
| LLM prompt quality | 5 | ~8h |
| User intent controls | 4 | ~15h |
| Schema e config | 3 | ~24h |
| Onboarding | 4 | ~11h |
| Feedback/status | 4 | ~8h |
| Erros | 3 | ~6h |
| Persistência | 4 | ~12h |
| UX polish | 6 | ~13h |
| Documentação | 4 | ~12h |
| Deploy multi-user | 4 | ~14h |
| **Total** | **41** | **~123h** |

**Realista:** 60-70h se cortar backlog (P2/P3) e priorizar P0/P1.

---

## Trilhas

**Trilha "produto usável single-user" (~40h):**
Fix P0: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 4.1, 5.1, 6.1, 7.1, 10.1.
Isso vira uma ferramenta que designer indie de jogo consegue realmente usar localmente pra prototipar.

**Trilha "produto usável multi-user hospedado" (~90h):**
Trilha 1 + fixes P1 críticos (2.3, 2.4, 3.3, 4.2, 4.3, 8.1, 8.2, 10.2, 10.3) + Anthropic backend completo pra deploy.
Isso vira SaaS pequeno viável.

**Trilha "excelência" (~120h):**
Tudo, incluindo polish/docs/observability.

Decisão do humano.