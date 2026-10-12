# Plugin archeo para Codex

Skills para trabalhar com o [Archeo](https://archeo.cd2.com.br), as mesmas do pacote do Claude Code.

> As pastas `skills/` e `references/` deste pacote são **cópias geradas** de [`core/archeo`](../../../core/archeo). Edite lá e rode `python3 scripts/sync_plugins.py` na raiz do repositório.

Instalação:

```
codex plugin marketplace add cd2tec/archeo-harness-plugins
```

Depois, reinicie o app, abra o diretório de plugins, escolha o marketplace **Archeo (CD2 Retail Tech)** e instale o `archeo`.

**Requisito:** um conector do Archeo configurado como servidor MCP no Codex, com as ferramentas de consulta somente leitura (`db_*`).

**Diferença em relação ao Claude:** a `build-mcp-dashboard` entrega o painel como arquivo HTML, só no modo snapshot. Os modos ao vivo e agendado dependem de recursos do Claude (artefato com capability `mcp` e tarefa agendada) e ainda não têm equivalente aqui.

## spec-mcp-tool

Gera, pronta para copiar e colar, a ficha da tela **Nova ferramenta** do Archeo MCP Creator, para qualquer banco conectado ao Archeo.

A skill identifica o conector ativo na sessão, explora o banco (tabelas, colunas, amostras, volume, flags), escreve o SQL com parâmetros `$1..$n` no dialeto da engine e executa com valores de teste antes de entregar.

| Arquivo | Conteúdo |
|---|---|
| [`SKILL.md`](skills/spec-mcp-tool/SKILL.md) | Fluxo, formato da ficha e convenções de nome, descrição e limites |
| [`references/regras-sql.md`](skills/spec-mcp-tool/references/regras-sql.md) | Sintaxe por engine, tipos de parâmetro, filtros opcionais, diagnóstico de falhas e checklist |
| [`references/exemplo-ficha.md`](skills/spec-mcp-tool/references/exemplo-ficha.md) | Ficha completa sobre um banco fictício |

Exemplos de uso:

- "crie uma ferramenta no Archeo para títulos vencidos por cliente"
- "gere o SQL dessa consulta para cadastrar como ferramenta no MCP"
- "quais tipos uso nos parâmetros dessa ferramenta?"

## build-mcp-dashboard

Monta um dashboard executivo de varejo a partir do ERP ou PDV conectado ao Archeo e publica como artefato: totalizadores com variação, índice de saúde de 0 a 100, venda por dia, mapa de calor por dia e hora, rankings de departamentos, produtos, pagamentos, lojas e operadores, curva ABC e leitura com alertas.

| Arquivo | Conteúdo |
|---|---|
| [`SKILL.md`](skills/build-mcp-dashboard/SKILL.md) | Fluxo, escolha do modo de atualização |
| [`references/indicadores-varejo.md`](skills/build-mcp-dashboard/references/indicadores-varejo.md) | Mapeamento do ERP, catálogo de seções, consultas-modelo validadas |
| [`references/score.md`](skills/build-mcp-dashboard/references/score.md) | Componentes, pesos e limites do índice de saúde |
| [`references/modos-atualizacao.md`](skills/build-mcp-dashboard/references/modos-atualizacao.md) | Snapshot, ao vivo (capability `mcp`) e agendado |
| [`references/config.md`](skills/build-mcp-dashboard/references/config.md) | Formato do config do painel |
| [`assets/dashboard-template.html`](skills/build-mcp-dashboard/assets/dashboard-template.html) | Template sem dependências externas, claro e escuro |
| [`scripts/`](skills/build-mcp-dashboard/scripts) | Montagem com validação do config e pré-visualização em Chromium |

## analyze-mcp-*: relatórios de ERP de varejo

Oito skills, uma por módulo, que geram os relatórios clássicos de um ERP de varejo direto do banco conectado. Cada relatório tem colunas definidas, consulta-modelo e uma **prova de reconciliação** obrigatória; o que não fecha vira o primeiro item da entrega.

| Skill | Relatórios |
|---|---|
| [`analyze-mcp-estoque`](skills/analyze-mcp-estoque/SKILL.md) | Estoque geral, Kardex, análise de lote de inventário, cobertura e ruptura, estoque sem venda, inconsistências de saldo, giro, posição retroativa |
| [`analyze-mcp-vendas`](skills/analyze-mcp-vendas/SKILL.md) | ABC de venda, venda por cliente e segmento, produto final x componentes, comparativo de períodos, devoluções, carteira de clientes |
| [`analyze-mcp-compras`](skills/analyze-mcp-compras/SKILL.md) | ABC de abastecimento, sugestão de compra, pedidos pendentes, nível de serviço do fornecedor, variação de custo, pedido x nota, concentração de fornecedores |
| [`analyze-mcp-precos`](skills/analyze-mcp-precos/SKILL.md) | Margem, margem negativa, custo sem repasse, alterações de preço, resultado de promoção, preço de cadastro x praticado |
| [`analyze-mcp-perdas`](skills/analyze-mcp-perdas/SKILL.md) | Quebra por motivo, perda identificada e não identificada, validade, ajustes manuais, exceções de frente de caixa, trocas e devoluções |
| [`analyze-mcp-fiscal`](skills/analyze-mcp-fiscal/SKILL.md) | Documentos fiscais sintético e analítico, cabeçalho x itens, entradas x saídas por CFOP, resumo de tributos, sequência de numeração, cadastro tributário, campos de IBS, CBS e IS |
| [`analyze-mcp-contabil`](skills/analyze-mcp-contabil/SKILL.md) | Balancete, razão, diário, resultado gerencial, integridade dos lançamentos, conciliação módulo x contábil, posição do LALUR |
| [`analyze-mcp-financeiro`](skills/analyze-mcp-financeiro/SKILL.md) | Contas a pagar e a receber por vencimento, inadimplência, fluxo de caixa, prazos médios e ciclo, cartões, bancos, exceções |

Estrutura comum:

| Arquivo | Conteúdo |
|---|---|
| [`references/metodo-analise.md`](references/metodo-analise.md) | Método compartilhado: fluxo, regras de consulta, formato da entrega, volume e exportação, dados pessoais, checklist |
| `skills/analyze-mcp-<módulo>/SKILL.md` | Roteamento do pedido para o relatório, defaults de escopo, particularidades do domínio e provas obrigatórias |
| `skills/analyze-mcp-<módulo>/references/relatorios.md` | Mapeamento do ERP (termos de busca), o que medir, colunas e consultas-modelo de cada relatório |

As skills são agnósticas de ERP: tabelas e colunas saem da exploração do banco conectado. Fiscal e contábil entregam **conferência gerencial**, não escrituração oficial. Um relatório que será pedido de novo pode virar ferramenta com `spec-mcp-tool`.

### Convenção de nomes

Skills do plugin seguem `[ação]-mcp-[recurso]`: `add` cria um ativo (ferramenta, painel), `analyze` produz um relatório ou análise de um módulo.

**Requisito de todas as skills:** um conector do Archeo ativo na sessão (ferramentas `db_*`).
