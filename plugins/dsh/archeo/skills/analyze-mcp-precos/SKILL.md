---
name: analyze-mcp-precos
description: Gera relatórios de preço, margem e promoção de um ERP de varejo a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre margem por produto e departamento, itens com margem negativa ou preço abaixo do custo, custo que subiu sem repasse ao preço, histórico de alteração de preço, resultado de promoção (antes, durante e depois) e divergência entre o preço de cadastro e o praticado no caixa. Use quando o usuário pedir análise de margem, markup, rentabilidade por produto ou categoria, itens vendidos abaixo do custo, alterações de preço, resultado ou efetividade de promoção, ou conferência de preço de um banco conectado ao Archeo.
---

# analyze-mcp-precos: relatórios de preço, margem e promoção a partir do banco conectado ao Archeo

Responde às perguntas do pricing: onde ganho, onde perco, o que mudou no custo e o que a promoção entregou.

Siga o método comum em `references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`.

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "margem por produto", "rentabilidade por categoria", "markup" | Margem | 3.1 |
| "o que vendo no prejuízo", "preço abaixo do custo" | Margem negativa | 3.2 |
| "custo subiu e o preço não" | Custo sem repasse | 3.3 |
| "o que mudou de preço", "histórico de preço" | Alterações de preço | 3.4 |
| "a promoção funcionou?", "resultado da oferta" | Resultado de promoção | 3.5 |
| "preço do sistema bate com o caixa?" | Preço de cadastro x praticado | 3.6 |

Pedido genérico ("análise de margem") recebe **margem por departamento** com os 20 itens de maior e de menor contribuição.

## Antes de qualquer margem: o teste do custo

Nenhum relatório de margem sai sem estes três números, medidos no período:

| Teste | Como | Consequência |
|---|---|---|
| Cobertura | % da venda com custo > 0 | Abaixo de 90%: margem só para a parcela coberta, com o aviso no topo |
| Dispersão | Diferença entre a maior e a menor margem por departamento | Abaixo de 1 ponto percentual: o custo é estimado por um percentual fixo, não real. Diga isso e não ranqueie por margem |
| Época do custo | O custo vem gravado no item vendido ou só existe o custo atual do cadastro? | Só custo atual: a margem de períodos passados é aproximada; declare |

A consulta de cobertura e dispersão está em `../build-mcp-dashboard/references/indicadores-varejo.md` (margem bruta).

## Definições (declare a que usou)

- **Margem bruta %** = (venda líquida - custo da mercadoria vendida) / venda líquida.
- **Markup %** = (preço - custo) / custo. Margem de 30% é markup de 42,9%: confundir os dois é o erro mais comum da área.
- **Margem de contribuição** desconta também impostos sobre a venda e despesas variáveis (taxa de cartão, comissão, frete). Só calcule com os impostos por item disponíveis; senão entregue a margem bruta e diga o que ficou de fora.
- **Contribuição em valor** (venda - custo) ordena melhor que margem %: item de margem alta e venda mínima não paga a conta.

Diga se venda e custo estão com ou sem impostos. Venda com imposto contra custo sem imposto infla a margem.

## O que preço tem de particular

1. **Preço é por loja e por data.** Tabela por loja, por cluster, por canal, por embalagem (unidade e atacarejo), com vigência. "O preço do produto" quase nunca é um número só.
2. **Preço praticado.** O valor unitário do item vendido já vem com desconto de promoção, de fidelidade, de operador. Preço médio praticado = venda líquida / quantidade.
3. **Promoção tem várias formas.** Preço de oferta com vigência, leve X pague Y, desconto por cliente, por quantidade, combo. Descubra onde cada uma é gravada e se o item vendido marca que saiu em promoção.
4. **Produto pesável e de produção** tem custo com quebra embutida; a margem do cadastro e a real divergem (cruze com `analyze-mcp-perdas`).
5. **Bonificação e verba** do fornecedor melhoram a margem real e raramente estão no custo do item. Sem esse dado, diga que a margem é a "de nota".

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| Margem | Venda do relatório = venda total do período; custo total = soma dos itens |
| Margem negativa | Cada item listado confere com preço e custo do cadastro ou do item vendido |
| Resultado de promoção | Venda dos itens promovidos no período = venda desses itens na fonte geral |
| Cadastro x praticado | Amostra de 5 divergências conferida no detalhe do item vendido |

## Entrega

Formato do método comum, com o teste do custo no bloco de premissas. A skill não altera preço: sugestões de remarcação saem como lista para decisão.

Relatórios que valem virar ferramenta (`spec-mcp-tool`): margem por departamento (`$1`, `$2` período, `$3` loja), itens com margem negativa (`$1`, `$2` período, `$3` loja) e custo sem repasse (`$1` dias, `$2` variação mínima %).
