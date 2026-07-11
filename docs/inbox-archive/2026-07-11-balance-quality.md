# INBOX — 2026-07-11 (Balance Studio)

Após executar, mova esta task pra `docs/inbox-archive/YYYY-MM-DD-hhmm.md` ou apague.

## Task: experimento de qualidade real de balanceamento (número-manchete de portfólio)

**Contexto:** você fez a autocrítica correta — "100% success" do B6.5 mediu validade de output (schema + parsing), não qualidade de balanceamento. Você propôs medir dispersão de winrate antes/depois de N iterações do Iterator. **Aprovado, com 3 ajustes que evitam gaming.**

**Objetivo:** produzir o número que vai no README/portfólio: **"Iterator reduziu dispersão de winrate em X% mantendo variedade em 3 domínios diferentes."** Isso vira a mensagem central do projeto — não "framework roda", mas "framework produz melhoria mensurável".

### Ação

**1. Métrica primária — dispersão:**

- Card game + Creature RPG: `winrate_std_dev` = desvio padrão do winrate por entidade
- Team composition: `completion_rate_std_dev` = desvio padrão da completion_rate entre 5 workloads variados (5 conjuntos diferentes de tasks — variabilidade = balance também é robustez)
- Menor = mais balanceado

**2. Métrica de guardrail — variedade preservada:**

Sem essa, o Iterator pode "balancear" nivelando tudo (nerfando standouts) → dispersão cai mas jogo/produto fica sem alma. Adicionar:

- Entropy de stats numéricos por entidade (ou distância média no espaço de atributos)
- Reportar delta de variedade junto com delta de dispersão
- **Se variedade cai >20%** enquanto dispersão cai, sinalizar no relatório: "Iterator pode estar homogeneizando em vez de balanceando"

**3. Múltiplas seeds pra ter intervalo de confiança:**

- 3 seeds por domain (ex: 42, 43, 44)
- Reportar média ± std entre seeds
- Sem isso, resultado bom pode ser sorte de uma seed

### Fluxo por domain

1. Design inicial (Fake ou LLM local — usar LLM local, é o que vende): brief padrão + N entidades
2. Medir `winrate_std_dev` (ou `completion_rate_std_dev`) e `variety` estado inicial
3. Rodar 5 iterações do `IteratorLlm` local — cada iteração: simulate → judge → propose_changes → apply
4. Medir dispersão e variedade após
5. Repetir passos 1-4 com 3 seeds diferentes
6. Agregar média ± std

### Formato do resultado (em `docs/experiments.md`)

```
## Experimento: qualidade de balanceamento (Iterator local)

Data: YYYY-MM-DD
Backend: local (Qwen2.5-Coder-7B via llama-server)

### card_game (10 unidades, 3 seeds)
  before iteration: winrate_std = 0.28 ± 0.03, variety = 3.4 ± 0.1
  after 5 iterations: winrate_std = 0.11 ± 0.02, variety = 3.2 ± 0.1
  delta: dispersão -61%, variedade -6%
  interpretação: Iterator reduziu desequilíbrio significativamente
                 mantendo variedade

### creature_rpg (100 creatures, 3 seeds)
  ... (mesmo formato)

### team_composition (50 pessoas, 3 workloads × 3 seeds)
  ... (mesmo formato)

### Conclusão
"Iterator reduziu dispersão de winrate em X% mantendo variedade em 3
domínios diferentes."
```

### Verificação (DoD)

- [ ] 3 domains rodados, resultado em `docs/experiments.md`
- [ ] Métrica de dispersão baixou em pelo menos 2 dos 3 domains (senão o Iterator não está agregando valor mensurável — reportar e discutir)
- [ ] Métrica de variedade documentada com delta em cada domain
- [ ] Média ± std entre 3 seeds reportada
- [ ] Nenhum guardrail violado (`variedade` não caiu >20% em nenhum domain)
- [ ] `pytest` inteiro continua verde (nenhum teste novo obrigatório, mas se implementar helpers reutilizáveis pra medir dispersão/variedade, testar eles)
- [ ] Número-manchete escrito em 1 linha no fim do experimento

### Depois

Sprint 8 continua: atualizar o README com o número-manchete no topo, gravar demo video mostrando o loop de iteração num domain (card_game é o mais visual), landing/GIF.

### Notas

- Se team_composition falhar em reduzir dispersão, é porque completion_rate é ruído demais em N=5 workloads — aumentar pra 10 workloads antes de declarar falha
- Iterator do 7B às vezes propõe pouco/inválido (você mesma anotou). Nesse caso rodar 8 iterações em vez de 5 pra dar mais chances de aplicar mudanças válidas
- Custo esperado: $0 (local, unlimited calls)
- Tempo: ~1-2h dependendo de latência do llama-server e quantas iterações rodam efetivas
