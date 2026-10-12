---
name: analyze-mcp-financeiro
description: Gera relatórios financeiros de um ERP de varejo a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre contas a pagar e a receber por vencimento (aging), inadimplência por cliente e por faixa de atraso, fluxo de caixa realizado e projetado, prazos médios de pagamento, recebimento e estoque com o ciclo financeiro, conciliação de cartões (venda contra recebível, taxas e antecipação), posição de bancos e tesouraria, e exceções como títulos em duplicidade ou baixas fora do padrão. Use quando o usuário pedir contas a pagar, contas a receber, títulos vencidos, inadimplência, aging, fluxo de caixa, previsão de caixa, prazo médio, ciclo financeiro, conciliação de cartão ou taxa de adquirente de um banco conectado ao Archeo.
---

# analyze-mcp-financeiro: relatórios financeiros a partir do banco conectado ao Archeo

Responde às perguntas do financeiro: quanto tenho a pagar e a receber, quando, quem está atrasado, se o caixa aguenta e se o cartão está pagando o que deve.

Siga o método comum em `references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`.

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "contas a pagar", "o que vence essa semana" | Contas a pagar por vencimento | 3.1 |
| "contas a receber", "títulos vencidos", "inadimplência" | Contas a receber e inadimplência | 3.2 |
| "fluxo de caixa", "previsão de caixa" | Fluxo de caixa | 3.3 |
| "prazo médio", "ciclo financeiro", "capital de giro" | Prazos médios e ciclo | 3.4 |
| "conciliação de cartão", "taxa da maquininha", "o cartão pagou?" | Cartões | 3.5 |
| "saldo dos bancos", "tesouraria" | Bancos e tesouraria | 3.6 |
| "título duplicado", "baixas estranhas" | Exceções | 3.7 |

Pedido genérico ("como está o financeiro") recebe **a pagar e a receber por faixa de vencimento**, lado a lado, com o saldo líquido por semana nas próximas quatro semanas.

## Defaults de escopo

- **Data de referência:** a última data com movimento financeiro no banco. Vencido é o que venceu antes dela, não antes de hoje.
- **Posição:** títulos em aberto na data de referência.
- **Valor:** saldo em aberto (valor original - baixas parciais), sem juros e multa calculados, a menos que o banco já os grave.
- **Faixas:** vencidos há mais de 90, 61 a 90, 31 a 60, 1 a 30 dias; a vencer em 1 a 7, 8 a 15, 16 a 30, 31 a 60, acima de 60 dias.

## O que financeiro tem de particular

1. **Título tem ciclo de vida.** Aberto, baixado parcial, liquidado, cancelado, renegociado, em cobrança, protestado, substituído. "Em aberto" é saldo > 0 em situação válida: liste as situações com contagem e valor e defina quais contam.
2. **Baixa não é só pagamento.** Devolução, abatimento, desconto, compensação entre pagar e receber, perda e substituição também baixam. Para fluxo de caixa realizado, só as baixas com movimento de dinheiro.
3. **Três datas.** Emissão, vencimento (original e prorrogado) e pagamento. Aging usa vencimento; fluxo realizado usa pagamento; prazo médio usa emissão e vencimento.
4. **Parcelas.** Um documento vira várias parcelas; conte títulos e documentos separadamente.
5. **Cartão e voucher no varejo.** A venda vira recebível da adquirente, com prazo e taxa, e pode ser antecipada. Em muitos ERPs o recebível de cartão mora num módulo próprio (TEF, conciliadora), fora do contas a receber.
6. **Previsto que não vira título.** Folha, impostos, aluguel e pedidos de compra ainda não faturados não estão no contas a pagar. Fluxo projetado só com títulos é **o piso das saídas**, e é preciso dizer isso.
7. **Empresa e filial.** Pagamento centralizado na matriz com título lançado na filial é comum. Decida o nível e declare.
8. **Dado pessoal e sensível.** Inadimplência por cliente pessoa física é dado pessoal com potencial de dano: código e nome, CPF mascarado, sem contato, e só para quem tem finalidade de cobrança ou crédito (método comum, seção 6).

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| A pagar, a receber | Soma das faixas = total em aberto; valor original - baixas = saldo, por título, numa amostra |
| Fluxo realizado | Saldo inicial + entradas - saídas = saldo final das contas de banco e caixa |
| Prazos médios | Compras e vendas usadas = totais dos módulos de origem no período |
| Cartões | Venda em cartão no caixa = recebíveis gerados (bruto) no mesmo período |

## Entrega

Formato do método comum. Em toda projeção, separe **realizado**, **previsto por título** e **não incluído**, e nunca apresente projeção como saldo.

Relatórios que valem virar ferramenta (`spec-mcp-tool`): a pagar por vencimento (`$1` data de referência, `$2` empresa, `$3` fornecedor), títulos vencidos por cliente (`$1` data de referência, `$2` dias mínimos de atraso) e fluxo previsto por dia (`$1`, `$2` período, `$3` empresa).
