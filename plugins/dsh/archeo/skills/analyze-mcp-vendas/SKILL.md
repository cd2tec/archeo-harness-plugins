---
name: analyze-mcp-vendas
description: Gera relatórios gerenciais de venda de um ERP de varejo ou distribuição a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre curva ABC de venda (por produto, cliente, segmento, vendedor ou fornecedor), venda e receita por cliente e segmento, produto final com seus componentes e rendimento (kits, receitas, produção própria), comparativo entre períodos e mesmas lojas, devoluções e cancelamentos, e carteira de clientes (positivação, recência, frequência e valor, inativos). Use quando o usuário pedir análise ABC de venda, ranking de clientes, venda por segmento ou canal, receita por cliente, rendimento de produto final, comparativo de vendas, devoluções ou clientes inativos de um banco conectado ao Archeo. Para um painel visual com totalizadores e gráficos, use build-mcp-dashboard.
---

# analyze-mcp-vendas: relatórios gerenciais de venda a partir do banco conectado ao Archeo

Responde às perguntas do módulo gerencial: quem compra, o quê, por qual canal, com que margem e o que mudou. Serve tanto ao varejo de loja (cupom) quanto ao atacado e à distribuição (pedido e nota por cliente).

Siga o método comum em `references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`. Para localizar venda por cupom e itens vendidos, aproveite o mapeamento de `../build-mcp-dashboard/references/indicadores-varejo.md`, seção 1.

**Esta skill ou o dashboard?** Painel para acompanhar a operação (cards, linha do tempo, mapa de calor) é `build-mcp-dashboard`. Aqui o resultado é um relatório analítico, com linhas, classes e prova, para decidir sobre sortimento, carteira e política comercial.

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "curva ABC de venda", "quais produtos fazem 80% da venda" | ABC de venda | 3.1 |
| "venda por cliente", "receita por segmento", "maiores clientes" | Venda por cliente e segmento | 3.2 |
| "produto final e componentes", "rendimento da receita", "kit" | Produto final x componentes | 3.3 |
| "comparado com o ano passado", "mesmas lojas" | Comparativo de períodos | 3.4 |
| "devoluções", "trocas", "cancelamentos" | Devoluções e cancelamentos | 3.5 |
| "clientes inativos", "positivação", "quem parou de comprar" | Carteira de clientes | 3.6 |

Pedido genérico ("análise de vendas") recebe a **ABC de venda por produto** com o resumo das classes e o sintético por departamento.

## Defaults de escopo

- **Período:** últimos 30 dias até a última data com venda; ABC e carteira usam 90 dias (30 dias classificam mal item de giro lento). Declare.
- **Medida:** venda líquida (sem cancelados, líquida de devolução e desconto). Diga qual coluna foi usada e o que ela inclui (impostos, frete, acréscimos).
- **Dimensão da ABC:** produto, por valor. Por quantidade ou por margem quando o usuário pedir; as três classificações divergem bastante e vale dizer isso.
- **Cortes ABC:** A até 80% do acumulado, B até 95%, C o restante. Ajustável.

## O que venda tem de particular

1. **Qual é a venda.** Bruta, líquida de desconto, líquida de devolução, com ou sem impostos, faturada ou pedida. Em distribuição, pedido, faturamento e entrega são datas e valores diferentes. Escolha uma, declare e não misture.
2. **Devolução não é venda negativa do mesmo dia.** Ela acontece em outro período e, em muitos ERPs, em outra tabela (nota de entrada de devolução). Decida se o relatório é por competência da venda original ou da devolução.
3. **Canal e segmento.** Loja, e-commerce, marketplace, televendas, atacado. O segmento pode estar no cliente, no pedido ou na tabela de preço. Meça o preenchimento antes de quebrar por ele.
4. **Cliente não identificado.** No varejo de loja, a maior parte dos cupons não tem cliente. Relatório por cliente cobre só a parcela identificada: informe o percentual da venda coberto.
5. **Margem depende do custo.** Antes de qualquer coluna de margem, meça cobertura e dispersão do custo como em `build-mcp-dashboard` (custo estimado gera margem uniforme e falsa).
6. **Mesmas lojas.** Comparar períodos com lojas que abriram ou fecharam mistura crescimento com expansão. Compare só as lojas com venda nos dois períodos e mostre o total à parte.
7. **Dado pessoal.** Ranking de clientes pessoa física usa código e nome; CPF mascarado; sem endereço ou contato (método comum, seção 6).

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| ABC | Soma das classes = venda total do período; participações somam 100% |
| Cliente e segmento | Venda identificada + não identificada = venda total |
| Produto final x componentes | Custo dos componentes x quantidade produzida = custo atribuído ao produto final (ou diferença explicada como perda) |
| Comparativo | Total = mesmas lojas + lojas novas + lojas encerradas |
| Devoluções | Devolução por motivo = devolução total |

## Entrega

Formato do método comum. Toda ABC traz o quadro de classes (itens, % dos itens, valor, % do valor) antes da lista.

Relatórios que valem virar ferramenta (`spec-mcp-tool`): ABC de venda (`$1` data inicial, `$2` data final, `$3` loja, `$4` departamento), venda por cliente (`$1`, `$2` período, `$3` segmento) e clientes inativos (`$1` dias sem compra).
