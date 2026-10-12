# Financeiro: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.7)

Consultas em SQL Server com marcadores `<assim>`; **[modelo]** até passarem na prova no banco conectado. O aging por faixa (3.1 e 3.2) e o acumulado por vencimento (3.3) são **[validado]** em Oracle 23, por consulta somente leitura direta ao banco (não pelo conector Archeo), com a soma das faixas igual ao total em aberto.

## 1. Mapeamento

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Títulos a pagar | Aging, fluxo | `titulo_pagar`, `contas_pagar`, `cap`, `pagar`, `duplicata`, `obrigacao`, `payable` | Valor original, saldo, emissão, vencimento, pagamento, situação, fornecedor, espécie |
| Títulos a receber | Aging, inadimplência | `titulo_receber`, `contas_receber`, `car`, `receber`, `crediario`, `convenio`, `receivable` | Idem; portador, forma de cobrança |
| Baixas | Realizado, prazos | `baixa`, `liquidacao`, `pagamento`, `recebimento`, `quitacao` | Tipo da baixa (dinheiro ou não), data, juros, desconto, conta bancária |
| Movimento bancário e caixa | Fluxo realizado, saldos | `movimentacao_bancaria`, `mov_banco`, `extrato`, `tesouraria`, `caixa`, `conta_corrente` | Saldo inicial, sentido, conciliado ou não |
| Plano financeiro | Quebra do fluxo | `plano_financeiro`, `natureza`, `categoria`, `centro_custo`, `historico` | Grupos de entrada e saída |
| Cartões | Conciliação | `cartao`, `adquirente`, `bandeira`, `tef`, `nsu`, `autorizacao`, `taxa`, `antecipacao`, `lote_cartao` | Venda bruta, taxa, líquido, previsão e data de crédito |
| Parceiro | Quebras | `cliente`, `fornecedor`, `pessoa` | Tipo (PF ou PJ), limite de crédito, situação |

Uma tabela única de títulos com indicador de pagar ou receber é comum: confirme o indicador antes de somar.

## 2. O que medir

- Títulos por situação e por espécie: contagem, valor original e saldo.
- Vencimentos: menor e maior data; títulos em aberto com vencimento muito antigo (provável sujeira).
- Baixas por tipo; % de baixas com conta bancária.
- Movimento bancário: período, contas, % conciliado.
- Indicador de pagar ou receber: liste os valores distintos. Código fora do par esperado (um terceiro valor, por exemplo) não entra em nenhum dos lados até o usuário dizer o que é.
- Data de pagamento: % preenchido nos títulos quitados. Quitado sem data de quitação é comum em carga e migração, e inviabiliza prazo praticado e fluxo realizado por título: diga isso em vez de usar outra data no lugar.
- Tabelas vazias: o financeiro pode rodar em outro sistema. Se títulos e movimento estiverem vazios, diga isso e pare.

## 3. Relatórios

### 3.1 Contas a pagar por vencimento

**Colunas (sintético):** faixa, títulos, valor em aberto, % do total. **Por fornecedor:** os 20 maiores, com vencido e a vencer. **Agenda:** por dia nos próximos 30 dias.

```sql
SELECT x.faixa, COUNT(*) titulos, CAST(SUM(x.saldo) AS float) valor,
       CAST(100.0 * SUM(x.saldo) / NULLIF(SUM(SUM(x.saldo)) OVER (), 0) AS float) part_pct
FROM (SELECT t.<saldo> saldo,
             CASE WHEN d.dias < -90 THEN '1 vencido > 90'
                  WHEN d.dias < -60 THEN '2 vencido 61-90'
                  WHEN d.dias < -30 THEN '3 vencido 31-60'
                  WHEN d.dias <   0 THEN '4 vencido 1-30'
                  WHEN d.dias <=  7 THEN '5 a vencer 0-7'
                  WHEN d.dias <= 15 THEN '6 a vencer 8-15'
                  WHEN d.dias <= 30 THEN '7 a vencer 16-30'
                  WHEN d.dias <= 60 THEN '8 a vencer 31-60'
                  ELSE '9 a vencer > 60' END faixa
      FROM <titulo_pagar> t
      CROSS APPLY (SELECT DATEDIFF(day, <data_referencia>, t.<vencimento>) dias) d
      WHERE <em_aberto> AND t.<saldo> > 0
        AND t.<empresa> = COALESCE(NULLIF(<empresa>, 0), t.<empresa>)) x
GROUP BY x.faixa
ORDER BY x.faixa OFFSET 0 ROWS
```

Se o conector recusar `CROSS APPLY`, repita o `DATEDIFF` no `CASE`. O prefixo numérico na faixa garante a ordem.
Em Oracle: `TRUNC(t.<vencimento>) - <data_referencia>` no lugar do `DATEDIFF`, `CROSS APPLY (SELECT ... FROM dual)`, `NVL` ou `COALESCE`, e `ORDER BY` simples. Quando não houver coluna de saldo, use `valor nominal - COALESCE(valor pago, 0)` e confira numa amostra.
A pagar vencido há muito tempo raramente é dívida real: costuma ser título pago por fora e não baixado, ou em disputa. Destaque como item a sanear.
**Prova:** soma das faixas = total em aberto; para 5 títulos, original - baixas = saldo.

### 3.2 Contas a receber e inadimplência

Mesmo aging de 3.1, sobre os títulos a receber, mais:

| Indicador | Fórmula | Declare |
|---|---|---|
| Inadimplência % | Vencido há mais de N dias / carteira total (aberto + vencido) | N (default 30) e o denominador |
| Inadimplência sobre faturamento | Vencido do que foi emitido no período / emitido no período | Safra analisada |
| Atraso médio | Média de dias de atraso ponderada pelo saldo | |
| Concentração | Participação dos 10 maiores devedores no vencido | |

**Por cliente:** saldo vencido, a vencer, maior atraso, limite de crédito e % utilizado, última compra.
**Por safra (opcional):** para cada mês de emissão, % ainda em aberto hoje: mostra se a inadimplência está piorando nas vendas recentes, o que o aging sozinho esconde.
Separe por espécie: crediário próprio, boleto, convênio, cheque e cartão têm comportamento e risco diferentes; cartão não é inadimplência do cliente.
**Prova:** soma das faixas = total em aberto.

### 3.3 Fluxo de caixa

**Realizado:** por dia ou semana: saldo inicial, entradas por grupo, saídas por grupo, saldo final.
**Projetado:** saldo atual + títulos a receber por vencimento - títulos a pagar por vencimento, por dia ou semana, com saldo acumulado e a primeira data de saldo negativo.

```sql
SELECT CONVERT(varchar(10), x.dia, 23) dia,
       CAST(x.entradas AS float) entradas, CAST(x.saidas AS float) saidas,
       CAST(<saldo_atual> + SUM(x.entradas - x.saidas) OVER (ORDER BY x.dia ROWS UNBOUNDED PRECEDING) AS float) saldo_projetado
FROM (SELECT u.dia, SUM(u.entra) entradas, SUM(u.sai) saidas
      FROM (SELECT CAST(r.<vencimento> AS date) dia, r.<saldo> entra, 0 sai
            FROM <titulo_receber> r
            WHERE <em_aberto_r> AND r.<vencimento> >= <data_referencia> AND r.<vencimento> < DATEADD(day, 30, <data_referencia>)
            UNION ALL
            SELECT CAST(p.<vencimento> AS date), 0, p.<saldo>
            FROM <titulo_pagar> p
            WHERE <em_aberto_p> AND p.<vencimento> >= <data_referencia> AND p.<vencimento> < DATEADD(day, 30, <data_referencia>)) u
      GROUP BY u.dia) x
ORDER BY x.dia OFFSET 0 ROWS
```

**Premissas que precisam estar na entrega:**
- Vencidos a receber: fora da projeção por default (ou em linha própria "vencido, recebimento incerto"). Somar vencido como entrada do dia infla o caixa.
- Vencidos a pagar: entram no primeiro dia, em linha própria.
- Cartão: pela data prevista de crédito, líquido de taxa, se o dado existir.
- **Não incluído:** vendas futuras à vista, folha, impostos, aluguel, compras ainda não faturadas, investimentos. A projeção é o que já está contratado em título; liste o que ficou de fora.

Ofereça cenário quando fizer sentido: recebimento com o atraso médio histórico aplicado (3.2) contra recebimento no vencimento.
**Prova (realizado):** saldo inicial + entradas - saídas = saldo final, por conta.

### 3.4 Prazos médios e ciclo

| Indicador | Fórmula |
|---|---|
| PMR, prazo médio de recebimento | Contas a receber médio / venda a prazo do período x dias; ou média de (vencimento - emissão) ponderada pelo valor |
| PMP, prazo médio de pagamento | Fornecedores médio / compras do período x dias; ou média ponderada de (vencimento - emissão) |
| PME, prazo médio de estoque | Estoque médio a custo / custo da mercadoria vendida x dias (`analyze-mcp-estoque`, 3.7) |
| Ciclo operacional | PME + PMR |
| Ciclo financeiro | PME + PMR - PMP |

Mostre o prazo **contratado** (emissão ao vencimento) e o **praticado** (emissão ao pagamento) lado a lado: a diferença é o atraso real, dos dois lados.
No varejo alimentar o ciclo financeiro costuma ser curto ou negativo (vende à vista, paga a prazo). Diga o que o número significa para a necessidade de capital de giro, sem comparar com referência externa sem fonte.
**Prova:** vendas e compras usadas = totais dos módulos de origem.

### 3.5 Cartões

**Colunas por adquirente e bandeira, por modalidade (débito, crédito à vista, parcelado, voucher):** transações, venda bruta, taxa em valor, taxa efetiva %, líquido previsto, líquido creditado, diferença, prazo médio de crédito, valor antecipado e custo da antecipação.

**Conferências:**
1. Venda em cartão no caixa (finalizadoras) = recebíveis gerados no mesmo período. Diferença aponta venda não integrada ou forma de pagamento trocada no caixa.
2. Taxa efetiva (taxa / bruto) por modalidade contra a taxa cadastrada ou contratada, se o usuário informar.
3. Recebíveis com data prevista vencida e sem crédito: liste por adquirente e data.
4. Chargebacks e cancelamentos.

Sem módulo de cartão no banco, só a conferência 1 no nível agregado é possível: diga isso. A conciliação transação a transação com o extrato da adquirente depende de um arquivo que não está no ERP.

### 3.6 Bancos e tesouraria

**Colunas:** conta, saldo inicial, entradas, saídas, saldo final, lançamentos não conciliados (quantidade e valor), data do último lançamento.
Fundo de troco, sangrias e depósitos por loja, quando houver tesouraria: diferença de caixa (sobra e falta) por loja e por operador, com a base de fechamentos.

### 3.7 Exceções

Cada uma com contagem, valor e amostra:
- títulos em duplicidade (mesmo parceiro, documento ou valor e vencimento);
- baixa com data anterior à emissão;
- baixa com desconto ou abatimento acima de um percentual (default 10%);
- títulos em aberto com vencimento há mais de um ano;
- pagamento a fornecedor sem nota de entrada vinculada;
- alteração de vencimento repetida no mesmo título;
- títulos a receber de cliente bloqueado com venda nova no período.

São itens para revisão; duplicidade aparente pode ser parcela legítima de mesmo valor.
