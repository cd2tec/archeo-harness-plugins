---
name: analyze-mcp-contabil
description: Gera relatórios de conferência contábil de um ERP a partir do banco conectado ao Archeo, com cada número reconciliado. Cobre balancete de verificação (saldo anterior, débitos, créditos e saldo atual por conta, em qualquer nível do plano), razão de uma conta, diário por período, demonstração de resultado gerencial, partidas dobradas que não fecham e lançamentos fora do padrão, conciliação entre os módulos e a contabilidade (estoque, contas a pagar e a receber contra a conta contábil) e posição das adições e exclusões do LALUR quando o ERP as controla. Use quando o usuário pedir balancete, razão, diário, DRE, conferência de lançamentos, conciliação contábil ou LALUR de um banco conectado ao Archeo. Não gera livros oficiais nem demonstrações para publicação.
---

# analyze-mcp-contabil: relatórios de conferência contábil a partir do banco conectado ao Archeo

Responde às perguntas de quem fecha e de quem lê a contabilidade: quanto tem em cada conta, o que compôs o saldo, se os lançamentos fecham e se a contabilidade bate com os módulos de origem.

Siga o método comum em `references/metodo-analise.md`. Mapeamento, colunas, consultas-modelo e provas estão em `references/relatorios.md`.

## Limite desta skill (diga na entrega)

**Conferência gerencial, não escrituração.** Diário, Razão e demonstrações oficiais são emitidos pelo sistema contábil, com termo de abertura e encerramento, assinados pelo contador e entregues na ECD (Escrituração Contábil Digital). O LALUR (Livro de Apuração do Lucro Real) hoje é escriturado na ECF (Escrituração Contábil Fiscal). O que esta skill entrega é a leitura dos mesmos lançamentos para análise, conferência e auditoria interna.

Toda entrega leva no cabeçalho: `Conferência gerencial. Não substitui a escrituração contábil oficial.`

## Relatórios

| O usuário pede | Relatório | Seção |
|---|---|---|
| "balancete", "saldo das contas" | Balancete de verificação | 3.1 |
| "razão da conta X", "o que compõe esse saldo" | Razão | 3.2 |
| "diário", "lançamentos do dia" | Diário | 3.3 |
| "DRE", "resultado do mês" | Resultado gerencial | 3.4 |
| "os lançamentos fecham?", "lançamentos estranhos" | Integridade dos lançamentos | 3.5 |
| "contabilidade bate com o estoque / financeiro?" | Conciliação módulo x contábil | 3.6 |
| "LALUR", "adições e exclusões" | Posição do LALUR | 3.7 |

Pedido genérico ("me dá a contabilidade do mês") recebe o **balancete no nível 3 do plano** com a prova de débito = crédito.

## Defaults de escopo

- **Período:** o último mês com lançamentos, por data de competência. Balancete acumulado desde o início do exercício.
- **Empresa:** uma por vez. Consolidado só quando o usuário pedir, com as eliminações entre empresas apontadas como não feitas.
- **Nível:** sintético no nível 3; analítico sob pedido ou para as contas com maior movimento.
- **Lançamentos:** só os efetivados. Rascunho, pendente de aprovação e estornado ficam fora e são contados à parte.

## O que contábil tem de particular

1. **Lançamento em partida dobrada tem três formatos comuns:** uma linha com conta débito e conta crédito; uma linha por conta com indicador D ou C; uma linha por conta com valor com sinal. Identifique o formato antes de somar: no primeiro, cada linha entra duas vezes (uma em cada conta).
2. **Natureza da conta.** Ativo e despesa são devedoras; passivo, patrimônio líquido e receita são credoras. Saldo = saldo anterior + débitos - créditos nas devedoras e o inverso nas credoras. Mostre o saldo com D ou C em vez de sinal.
3. **Plano de contas é uma árvore.** Lançamento só em conta analítica; a sintética soma as filhas. Descubra como a hierarquia é guardada (máscara do código `1.1.01.001`, coluna de conta pai, coluna de nível) para totalizar.
4. **Saldo anterior** vem de uma tabela de saldos mensais, se existir, ou da soma de todos os lançamentos anteriores. Com encerramento de exercício, contas de resultado zeram: não some através do lançamento de encerramento.
5. **Lançamentos de encerramento e de abertura** distorcem o resultado do mês em que ocorrem. Identifique (tipo, histórico, lote) e exclua da demonstração de resultado.
6. **Competência x data de lançamento.** O lançamento pode ter data de digitação diferente da competência. Use a competência e diga.
7. **Centro de custo e filial** são dimensões paralelas ao plano. Meça o preenchimento antes de quebrar por elas.
8. **Varejo:** a integração do estoque e do custo da mercadoria vendida costuma ser por lote mensal ou diário; receita vem do fiscal. Contabilidade "atrasada" em relação aos módulos é comum: informe a data do último lançamento integrado de cada origem.

## Prova obrigatória por relatório

| Relatório | Prova |
|---|---|
| Balancete | Total de débitos = total de créditos no período; soma dos saldos devedores = soma dos credores; ativo = passivo + patrimônio líquido + resultado do exercício |
| Razão | Saldo anterior + débitos - créditos = saldo final = saldo da conta no balancete |
| Diário | Débitos = créditos em cada lançamento e no dia |
| Resultado gerencial | Resultado = variação das contas de resultado no balancete |
| Conciliação | Diferença explicada item a item, ou apresentada como não explicada |

Balancete que não fecha não é entregue como balancete: entregue a diferença, o período em que ela nasce e os lançamentos candidatos (3.5).

## Entrega

Formato do método comum, com o aviso de conferência no cabeçalho. Valores em colunas de débito, crédito e saldo com indicador D ou C.

Relatórios que valem virar ferramenta (`spec-mcp-tool`): balancete (`$1` empresa, `$2` data inicial, `$3` data final, `$4` nível) e razão (`$1` empresa, `$2` conta, `$3`, `$4` período).
