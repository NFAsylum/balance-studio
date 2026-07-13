> **Note:** This document discusses design considerations that reference commercial games by name for comparative and structural purposes. See README `## Legal` section for full non-affiliation disclosure.

# INBOX — 2026-07-13 (Balance Studio — IP Hygiene)

Após executar, mova pra `docs/inbox-archive/2026-07-13-ip-hygiene.md`.

## Contexto

Auditoria legal do repo identificou 5 pontos de exposição IP. Nenhum é catastrófico, mas correção é barata (~2h total) e reduz risco significativamente. **Executar agora**, antes do repo crescer mais em visibilidade.

**Precedente jurídico consultado:**
- **Trademark law (Lanham Act):** nominative fair use requer não-endosso — disclaimer factual é elemento positivo
- **Copyright law:** disclaimer factual reduz statutory damages (Sega v. Accolade 1992)
- **Nominative fair use** confirmado em New Kids v. News America 1992
- **Padrão da categoria** (framework OSS com LLM generative): Machinations, LangChain, SillyTavern operam sem filter list — precedente de mercado

**Filosofia da correção:** posicionar Balance Studio na mesma categoria legal de Machinations/LangChain (tool provider, non-endorsing, nominative use). Nem paranóico, nem exposto.

## Ordem sequencial

Todas as tasks têm DoD verificável. Não há autorização pra pular nenhuma — cada uma tem função legal específica identificada.

---

### T-IP.1 [30min] Rename preset filenames

Trocar filenames em `presets/`:

| De | Para |
|---|---|
| `card_game/hearthstone.json` | `card_game/modern-mana-tcg.json` |
| `card_game/mtg.json` | `card_game/multi-color-tcg.json` |
| `card_game/yugioh.json` | `card_game/high-scale-duel.json` |
| `card_game/slay-the-spire.json` | `card_game/energy-roguelike.json` |
| `creature_rpg/pokemon-gen1.json` | `creature_rpg/elemental-creatures-classic.json` |
| `creature_rpg/dark-souls.json` | `creature_rpg/soulslike-enemies.json` |
| `creature_rpg/monster-hunter.json` | `creature_rpg/giant-beast-hunt.json` |

Atualizar toda referência a esses filenames em:
- Código (imports, `core/presets.py`, testes)
- Docs internas (README, architecture.md, writing-a-domain, writing-a-view, writing-a-preset se existir)

Atualizar também o campo `id` dentro de cada JSON pra bater com o novo filename (ex: `"id": "modern-mana-tcg"`).

**DoD:**
- Filenames renomeados
- Todo import/referência atualizado
- `pytest` verde
- `grep -rE "hearthstone|yugioh|mtg|slay-the-spire|pokemon-gen1|dark-souls|monster-hunter" --include="*.py" --include="*.json"` fora de `docs/inbox-archive/` retorna zero

### T-IP.2 [30min] Atualizar campos JSON pra nominativo

Em cada preset renomeado:

**Campo `name`:** descritivo genérico, não trademark cru.
- ❌ `"Hearthstone"` → ✅ `"Modern Mana-based TCG"`
- ❌ `"Magic: The Gathering"` → ✅ `"Multi-color Strategy TCG"`
- ❌ `"Yu-Gi-Oh!"` → ✅ `"High-scale Duel TCG"`
- ❌ `"Slay the Spire"` → ✅ `"Energy-based Roguelike Deckbuilder"`
- ❌ `"Pokemon (Gen 1)"` → ✅ `"Elemental Creature Collector (Classic)"`
- ❌ `"Dark Souls"` → ✅ `"Soulslike Enemies"`
- ❌ `"Monster Hunter"` → ✅ `"Giant Beast Hunt"`

**Campo `description`:** uso nominativo comparativo, **sem** atribuir ownership possessivo.

Padrão:
- ❌ `"Blizzard's Hearthstone: minions on a 0-10 mana curve..."` (atribui ownership)
- ✅ `"Structural preset inspired by digital TCGs like Hearthstone. Minions on a 0-10 mana curve, HP up to 30, attack up to ~16."` (nominativo comparativo)

Referenciar o jogo por nome **é permitido** — fair use nominativo é firme. **Não pode:**
- Usar possessivo ("Blizzard's ...", "Wizards' ...")
- Reproduzir taglines/slogans
- Copiar descrições verbatim

**Também atualizar preset MTG's `ability_kind` enum:**
- ❌ `["burn", "lifegain", "counter", "cantrip"]` (terminologia MTG-específica identificável)
- ✅ `["direct_damage", "restore_life", "negate", "card_draw"]`

Se houver `sim_config.ability_map` mapeando esses termos, atualizar:
- `"burn": "deal_damage"` → `"direct_damage": "deal_damage"`
- etc.

**DoD:**
- 7 presets com `name` genérico e `description` nominativa
- MTG preset com enum genérico + ability_map atualizado
- `pytest` verde
- Nenhum campo `name` de preset contém trademark cru

### T-IP.3 [5min] Disclaimer factual no README

Adicionar seção `## Legal` ao README, **imediatamente após o headline/pitch** (antes de "How it works"):

```markdown
## Legal

Balance Studio is an independent open-source project not affiliated with,
endorsed by, or sponsored by Blizzard Entertainment, Wizards of the Coast,
Hasbro, Konami, Nintendo, The Pokémon Company, FromSoftware, Bandai Namco,
Capcom, Mega Crit Games, or any other game publisher. Trademarks referenced
in comparative descriptions belong to their respective owners.
```

**CRÍTICO — NÃO adicionar** os seguintes elementos (aumentam exposição, não reduzem):

- ❌ Frases apologéticas: *"we do not intend to infringe..."*, *"we hope..."*
- ❌ Admissão de conhecimento de risco: *"this software may occasionally generate content that resembles..."*
- ❌ Convite pra contato: *"please report violations..."*, *"if you believe content violates..."*
- ❌ Long defenses ou justificativas: manter o texto curto e factual

**Justificativa (precedente):**
- **Disclaimer factual breve** = evidence de good faith (Sega v. Accolade 1992), reduz willful damages
- **Disclaimer apologético/admissivo** = evidence de conhecimento não-mitigado, aumenta willful damages
- Não é intuição — é distinção jurídica documentada

**DoD:**
- README tem seção `## Legal` com o texto acima (ou variação sinônima mantendo caráter factual)
- Nenhuma frase apologética/admissiva/convidativa presente
- Seção posicionada após headline principal, antes de content técnico

### T-IP.4 [30min] Prompt hardening no Designer/Iterator

Adicionar bloco `Content originality requirement` ao system prompt em ambos:
- `core/llm_local.py::LocalDesigner._SYSTEM` (ou onde o system prompt está definido)
- `core/llm_anthropic.py::AnthropicDesigner._SYSTEM` (mesma coisa)
- Análogo pro Iterator em ambos os arquivos

**Texto a adicionar** (colar como parágrafo adicional ao system prompt existente):

```
Content originality requirement:
- Generate 100% original names and entities. Do not reuse or approximate
  names of specific characters, cards, monsters, or entities from existing
  copyrighted games (Pokémon, Yu-Gi-Oh!, Magic: The Gathering, Hearthstone,
  Dark Souls, Monster Hunter, or any other IP).
- If the brief mentions a game by name, treat it only as tonal or structural
  guidance — never as a source of specific names, character traits, or
  proprietary content.
- When uncertain whether a name might be protected, invent something new
  that fits the theme without matching known IP.
```

Pro Iterator, adaptar ligeiramente:

```
Content originality requirement:
- When proposing modifications, do not introduce names or entities that
  approximate characters, cards, or content from existing copyrighted games.
- If modifying an entity name, generate an original replacement.
- Preserve originality standard equivalent to Designer output.
```

**DoD:**
- System prompts atualizados nos 4 arquivos (Designer local, Designer anthropic, Iterator local, Iterator anthropic)
- Teste manual: brief `"epic fantasy dragons and knights, magical combat"` gera nomes que **não** incluem "Blue-Eyes White Dragon", "Charizard", "Serra Angel", "Lightning Bolt", etc.
- Se algum teste existente valida output específico com trademark, ajustar teste (não relaxar prompt)

### T-IP.5 [15min] Reformular menções em `docs/architecture.md`

Buscar e reformular referências IP:

```bash
grep -nE "Pokémon|Pokemon|Yu-Gi-Oh|YuGiOh|Hearthstone|Magic.the.Gathering|MTG|Dark Souls|Monster Hunter|Slay.the.Spire" docs/architecture.md
```

Cada match: reformular de forma descritiva neutra.

Exemplos:
- `"a Pokémon 18-type chart"` → `"an 18-type elemental chart (common in creature-collector RPGs)"`
- `"Hearthstone-style mana curve"` → `"a bounded mana-curve system (0-10 range)"`
- `"YuGiOh scale (LP 8000)"` → `"a high-scale duel format (LP 8000)"`

**DoD:**
- Grep dessas strings em `docs/architecture.md` retorna zero
- Sem perda de conteúdo semântico (leitor entende igualmente o que a arquitetura faz)

---

## Cortado do escopo (com justificativa)

Rejeitado por não ser padrão da categoria ou aumentar exposição:

**❌ Filter list de nomes protegidos.**
Motivo: Machinations, LangChain, SillyTavern (todos framework OSS com componente generative equivalente) não implementam. Adiciona 1h + manutenção contínua sem ROI legal proporcional. Categoria de defesa "diligente" já é alcançada com prompt hardening + rename + disclaimer.

**❌ Renomear `.tsx` files (`HearthstoneStyle.tsx`, `YuGiOhStyle.tsx`).**
Motivo: código interno, visibilidade legal muito baixa. Recruiter olhando código vê "Hearthstone" mas é claramente descritivo/estrutural, não distributivo. Refactor grande sem ganho jurídico proporcional.

**❌ Disclaimer longo apologético.**
Motivo: aumenta exposição (ver T-IP.3). Precedente firme.

**❌ Alterar `docs/inbox-archive/*` e `docs/product-audit.md`.**
Motivo: working docs / auditoria interna. Contexto legal aceita histórico de trabalho. Referências neles são discussão técnica, não distribuição.

**❌ Atualizar `docs/writing-a-domain.md`, `docs/writing-a-view.md`, `docs/writing-a-preset.md`.**
Motivo: docs técnicas, uso descritivo em exemplos. Baixa exposição, similar a inbox-archive. Se aparecerem referências IP significativas, revisar caso a caso — mas não bulk.

---

## Verificação final

- [ ] `pytest` inteiro verde
- [ ] Grep de trademarks (Hearthstone, Pokemon, Yu-Gi-Oh, MTG, Dark Souls, Monster Hunter, Slay the Spire) em `presets/*.json`, `README.md`, `docs/architecture.md`, `core/prompts/*.txt`, `core/llm_*.py`:
  - Aparece em `.json` só em contextos comparativos ("inspired by") nas descriptions
  - Aparece em `README.md` só na seção Legal (não-afiliação)
  - Não aparece em `docs/architecture.md`
  - Não aparece em `core/prompts/*.txt` nem no system prompt dos hats (exceto lista de "do not use" no prompt hardening)
- [ ] Manual test: brief `"cyberpunk deck with dragons"` no LocalDesigner gera nomes originais (sem "Charizard-like", "Blue-Eyes", etc.)
- [ ] README `## Legal` seção existe, é factual, sem elementos apologéticos ou convidativos

## Diretiva sobre escopo

Execute a trilha completa. Todas as tasks. **Não corte T-IP.4 (prompt hardening)** — é a única defesa contra o risco real (LLM output de nomes protegidos). Rename + disclaimer sem prompt hardening deixa o mecanismo generative desprotegido.

Se algo travar tecnicamente (test que valida output com trademark, dep incompatível), escale imediatamente. Nunca decida corte sozinho.

### T-IP.6 [5min] Commit message expressivo do cleanup

Quando fizer o merge da branch dessa trilha pra `main`, usar mensagem estruturada abaixo (não uma linha curta genérica). Isso documenta INTENT no histórico — vira evidence de good faith se algum dia relevante.

```
chore: IP hygiene — nominative fair use compliance

- Rename preset filenames to generic descriptors
- Update `name` and `description` fields to nominative comparative use
- Add anti-infringement instruction to LLM Designer/Iterator prompts
- Add non-affiliation notice to README
- Reformulate specific IP mentions in architecture docs

Aligns with nominative fair use standard (New Kids v. News America 1992)
and industry practice for OSS frameworks with generative AI components
(LangChain, SillyTavern, Machinations).
```

**DoD:**
- Merge commit à main tem essa mensagem (ou variação sinônima que preserve os 4 pontos: rename + update fields + prompt hardening + non-affiliation notice + reference legal precedent)
- Não é single-line commit (mínimo 5 linhas de body descritivo)

### T-IP.7 [2min] Tag de versão marcando o cleanup

Após merge, criar tag anotada:

```bash
git tag -a v0.2-ip-clean -m "IP hygiene cleanup — nominative fair use compliant"
git push origin v0.2-ip-clean
```

Marca claramente quando o repo state passou pra "post-cleanup". Facilita qualquer defesa futura tipo "após 2026-07-13, repo state é X".

**DoD:**
- Tag `v0.2-ip-clean` existe local e no origin
- Tag é annotated (não lightweight — mensagem tem que estar visível)

### T-IP.8 [5min] Disclaimer breve nos docs internos

Adicionar linha no **topo** de:
- `docs/product-audit.md`
- Cada arquivo em `docs/inbox-archive/*.md` que menciona IPs específicos (grep pra identificar)

Texto exato (uma linha, antes de qualquer outro conteúdo):

```markdown
> **Note:** This document discusses design considerations that reference commercial games by name for comparative and structural purposes. See README `## Legal` section for full non-affiliation disclosure.
```

Isso contextualiza working docs sem admitir infração. Custo: 30s por arquivo.

**Não** modificar conteúdo dos docs — só adicionar a linha do disclaimer no topo. Manter integridade histórica das discussões técnicas.

**DoD:**
- `docs/product-audit.md` tem a linha no topo
- Cada `.md` em `docs/inbox-archive/` que grep encontra IP names tem a linha
- Grep de "This document discusses design considerations that reference" retorna >= 2 matches

### T-IP.9 [0min] Explicitamente NÃO fazer (regra crítica)

**Sob nenhuma circunstância:**

- ❌ `git filter-repo` ou `git filter-branch` pra reescrever histórico
- ❌ `git rebase -i` + squash pra colapsar commits antigos
- ❌ Force push sobrescrevendo `main`
- ❌ Delete + recreate do repo
- ❌ Marcar repo como private/archive

**Justificativa:** decisão do humano foi Opção A — aceitar histórico factual, focar cleanup adiante. Rewrite quebraria PRs #1-11 merged, forks eventuais, e sinalizaria pânico. Histórico atual (nominative fair use nas descriptions originais) é defensável; cleanup em progresso é evidence de good faith que **melhora** posição legal, não piora.

Se alguma parte da trilha exigir tocar histórico pra funcionar, escale IMEDIATAMENTE. Isso é red line.

---

## Após conclusão

- Move este arquivo pra `docs/inbox-archive/2026-07-13-ip-hygiene.md` (adicionando a linha de disclaimer T-IP.8 no topo dele também)
- Reporte no próximo prompt que trilha está pronta
- Inclua no report: link do commit de merge, link da tag `v0.2-ip-clean`