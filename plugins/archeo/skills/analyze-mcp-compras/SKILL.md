---
name: analyze-mcp-compras
description: Gera relatórios de compras e abastecimento de um ERP de varejo a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre curva ABC de abastecimento (por quantidade ou valor, cruzada com cobertura de estoque), sugestão de compra e reposição, pedidos em aberto e atrasados, nível de serviço do fornecedor (pedido x recebido, prazo), variação de custo de compra, divergência entre pedido e nota e concentração de fornecedores. Use quando o usuário pedir curva ABC de compras ou de abastecimento, sugestão de pedido, o que comprar, reposição, pedidos pendentes, atraso de fornecedor, desempenho de fornecedor, aumento de custo ou conferência de pedido contra nota de um banco conectado ao Archeo.
---

# analyze-mcp-compras: relatórios de compras e abastecimento a partir do banco conectado ao Archeo

Responde às perguntas do comprador: o que comprar, quanto, de quem, a que custo, e o quanto dá para confiar no fornecedor.

Siga o método comum em `../../references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`. Saldo de estoque e venda por item são mapeados como em `../analyze-mcp-estoque/references/relatorios.md`, seção 1.

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "curva ABC de abastecimento", "ABC de compras" | ABC de abastecimento | 3.1 |
| "o que comprar", "sugestão de pedido", "reposição" | Sugestão de compra | 3.2 |
| "pedidos em aberto", "o que está para chegar", "atrasados" | Pedidos pendentes | 3.3 |
| "desempenho do fornecedor", "quem atrasa", "entrega incompleta" | Nível de serviço do fornecedor | 3.4 |
| "o que subiu de custo", "variação de custo" | Variação de custo de compra | 3.5 |
| "pedido bate com a nota?", "divergência no recebimento" | Pedido x nota | 3.6 |
| "dependência de fornecedor" | Concentração de fornecedores | 3.7 |

Pedido genérico ("análise de compras") recebe a **ABC de abastecimento por valor cruzada com cobertura**, que é onde aparecem os dois erros caros: item A sem estoque e item C com estoque demais.

## Defaults de escopo

- **Período de demanda:** 90 dias até a última data com venda (30 dias para perecíveis, se o usuário indicar).
- **Dimensão da ABC:** produto, por valor de venda a custo (o que consome capital de giro). Por quantidade quando o usuário pedir: muda a ordem e a decisão logística.
- **Sugestão de compra:** por fornecedor ou por comprador, uma loja ou centro de distribuição por vez.
- **Pedidos pendentes:** todos os em aberto na data de referência.

## O que compras tem de particular

1. **Demanda não é venda.** Venda de item que ficou em ruptura subestima a demanda; venda em promoção superestima. Para a sugestão, use venda média dos **dias com saldo** quando der para saber, e sinalize itens que tiveram promoção no período.
2. **Embalagem de compra.** Pede-se em caixa, fardo ou palete, vende-se em unidade. Converta pelo fator de embalagem do fornecedor e arredonde a sugestão para cima no múltiplo.
3. **Prazo e frequência.** Sugestão sem lead time (prazo de entrega) e frequência de visita é chute. Se o ERP não guarda, calcule o prazo observado (data do recebimento - data do pedido) e declare.
4. **Custo de compra tem camadas.** Preço de tabela, descontos, bonificação, IPI (Imposto sobre Produtos Industrializados), ST (Substituição Tributária), frete, verba. Diga qual custo está na coluna usada. Bonificação entra com valor zero ou simbólico e derruba o custo médio aparente.
5. **Situação do pedido.** Aberto, parcial, atendido, cancelado, com saldo eliminado. "Pendente" = quantidade pedida - recebida - cancelada, e não a situação do cabeçalho.
6. **Abastecimento por CD (centro de distribuição).** Em rede com CD, a loja "compra" por transferência. Separe compra de fornecedor de transferência interna.

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| ABC de abastecimento | Soma das classes = total do período; cruzamento com estoque mantém o mesmo número de itens |
| Sugestão de compra | Cada parcela do cálculo (demanda, saldo, pendente) confere com sua fonte para uma amostra de 5 itens |
| Pedidos pendentes | Pedido = recebido + cancelado + pendente, por item |
| Nível de serviço | Recebimentos considerados = notas de entrada de compra do período |
| Pedido x nota | Valor da nota = soma dos itens conferidos |

## Entrega

Formato do método comum. **Sugestão de compra é sugestão:** entregue em planilha editável, com as colunas do cálculo abertas e as premissas de prazo, frequência e segurança visíveis, para o comprador ajustar. A skill não cria pedido no ERP.

Relatórios que valem virar ferramenta (`add-mcp-tool`): sugestão de compra (`$1` fornecedor, `$2` loja, `$3` dias de cobertura alvo), pedidos pendentes (`$1` fornecedor, `$2` loja) e variação de custo (`$1` data inicial, `$2` data final, `$3` variação mínima %).
