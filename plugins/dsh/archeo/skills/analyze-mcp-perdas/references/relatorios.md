# Perdas: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.6)

Consultas em SQL Server com marcadores `<assim>`; **[modelo]** até passarem na prova no banco conectado.

## 1. Mapeamento

Movimento, tipo de operação, inventário, produto e custo: `../../analyze-mcp-estoque/references/relatorios.md`, seção 1. Venda por cupom e operador: `../../build-mcp-dashboard/references/indicadores-varejo.md`, seção 1. Acrescente:

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Quebra | Perda identificada | `quebra`, `perda`, `avaria`, `baixa`, `descarte`, `sinistro` | Se é tabela própria, tipo de movimento ou nota de baixa; quantidade, custo, motivo |
| Motivo | Classificação | `motivo`, `causa`, `justificativa`, `tipo_quebra` | Distribuição real dos motivos e % em motivo genérico |
| Validade e lote | Vencidos | `validade`, `vencimento`, `lote`, `dta_validade`, `shelf` | Se o saldo é controlado por lote ou só a entrada tem validade |
| Ajuste | Ajustes manuais | tipo de movimento de `ajuste`, `acerto`, `correcao`; `usuario`, `observacao` | Quem lança, se exige motivo e aprovação |
| Cancelamento e desconto no caixa | Exceções | `cancelado`, `item_cancelado`, `desconto`, `supervisor`, `autorizacao` | Cancelamento de item x de cupom; desconto de promoção x manual; quem autorizou |

## 2. O que medir

- Onde a quebra está gravada (tabela própria, tipo de movimento, nota de baixa) e o total de cada fonte no mesmo mês, para escolher uma e não duplicar.
- Motivos: distribuição por ocorrências e por valor; % em motivo genérico ou vazio.
- Inventários: lotes encerrados no período, por loja e departamento.
- Cancelamentos e descontos: existem no nível do item e do cupom? Há operador, supervisor e hora?
- Validade: saldo por lote existe e está em uso?

## 3. Relatórios

### 3.1 Quebra por motivo e departamento

**Colunas:** departamento, motivo, ocorrências, quantidade, valor a custo, % do total de quebras, % sobre a venda do departamento.
**Analítico:** os 30 produtos de maior quebra em valor, com motivo predominante e % sobre a própria venda.

```sql
SELECT p.<cod_departamento>, q.<motivo>, COUNT(*) ocorrencias,
       CAST(SUM(q.<quantidade>) AS float) qtd,
       CAST(SUM(q.<quantidade> * COALESCE(q.<custo>, 0)) AS float) valor_custo,
       CAST(100.0 * SUM(q.<quantidade> * COALESCE(q.<custo>, 0))
            / NULLIF(SUM(SUM(q.<quantidade> * COALESCE(q.<custo>, 0))) OVER (), 0) AS float) part_pct
FROM <quebra> q
JOIN <produto> p ON p.<cod_produto> = q.<cod_produto>
WHERE q.<cod_loja> = COALESCE(NULLIF(<loja>, 0), q.<cod_loja>)
  AND q.<data> >= '2025-07-01' AND q.<data> < '2025-08-01'
GROUP BY p.<cod_departamento>, q.<motivo>
ORDER BY valor_custo DESC OFFSET 0 ROWS
```

Calcule o % sobre a venda com a venda do mesmo departamento, loja e período, em consulta separada, e junte no resultado. Referências de mercado para índice de perda variam por formato e por pesquisa: não cite um número de referência sem fonte; compare a operação com ela mesma (lojas entre si, período contra período).
**Prova:** total por motivo = total por departamento = total de quebras do período.
**Leituras típicas:** perecíveis concentrando a quebra (esperado; o que importa é a tendência e a loja fora da curva), vencimento em item com excesso de cobertura (problema de compra, cruze com `analyze-mcp-compras`), motivo genérico dominante.

### 3.2 Perda total: identificada e não identificada

**Colunas por departamento:** venda líquida, quebra identificada, falta de inventário, sobra de inventário, perda não identificada (falta - sobra), perda total, índice %, data do último inventário.

Monte em três consultas (quebras do período, divergência dos lotes de inventário encerrados no período, venda) e junte por departamento. A divergência de inventário segue `../../analyze-mcp-estoque/references/relatorios.md`, 3.3.

Cuidados:
- O período da perda não identificada é o intervalo **entre inventários**, não o mês do balanço. Um inventário anual concentra 12 meses de perda no mês em que ocorre: diga isso em vez de mostrar um pico falso.
- Quebra lançada entre o congelamento e a contagem pode estar nos dois lados.
- Liste os lotes considerados e os departamentos sem inventário.

### 3.3 Validade

**Vencidos em estoque:** produto, lote, validade, saldo do lote, valor a custo, dias vencido.
**A vencer:** faixas de 7, 15 e 30 dias, com saldo, venda média diária e a quantidade que não deve vender até o vencimento (saldo - venda média x dias restantes, se positiva): essa é a lista de ação (remarcar, transferir, doar).
Só é possível com saldo por lote. Com validade apenas na nota de entrada, entregue uma estimativa por entrada mais recente e marque como estimativa; sem validade em lugar nenhum, diga que o ERP não controla.

### 3.4 Ajustes manuais

**Colunas:** data, produto, loja, tipo (entrada ou saída), quantidade, valor a custo, motivo ou observação, usuário.
**Sintético:** por tipo e por loja: ocorrências, valor de entradas, valor de saídas, líquido, % sem motivo.
**Sinais de atenção:** ajuste de entrada e de saída no mesmo item em dias próximos, ajuste logo antes ou depois de inventário, concentração em um usuário, valores redondos, ajuste em itens de alto valor e fácil revenda.

### 3.5 Exceções de frente de caixa

**Colunas por operador (ou PDV, ou loja):** cupons, venda, cupons cancelados e valor, itens cancelados e valor, descontos manuais e valor, taxa de cada um sobre a própria venda, média da loja, quantas vezes acima da média.

```sql
SELECT v.<cod_operador>, COUNT(*) cupons,
       CAST(SUM(CASE WHEN <cancelado> THEN 0 ELSE v.<valor_liquido> END) AS float) venda,
       SUM(CASE WHEN <cancelado> THEN 1 ELSE 0 END) cupons_cancelados,
       CAST(SUM(CASE WHEN <cancelado> THEN v.<valor_liquido> ELSE 0 END) AS float) valor_cancelado,
       CAST(SUM(CASE WHEN <cancelado> THEN 0 ELSE COALESCE(v.<desconto>, 0) END) AS float) descontos
FROM <venda> v
WHERE v.<cod_loja> = <loja> AND v.<data> >= '2025-07-01' AND v.<data> < '2025-08-01'
GROUP BY v.<cod_operador>
HAVING COUNT(*) >= 100
ORDER BY valor_cancelado DESC OFFSET 0 ROWS
```

- O piso de cupons (100 por default) evita taxa alta por base pequena.
- Separe desconto de promoção e de fidelidade (regra do sistema) do desconto manual (decisão do operador ou supervisor). Sem essa distinção no dado, diga que o desconto mostrado inclui promoção.
- Itens cancelados depois do subtotal e cancelamento do cupom inteiro logo após o pagamento em dinheiro são os padrões clássicos de auditoria; só aponte se o dado tiver hora e forma de pagamento.

**Prova:** cancelado + válido = total registrado do período.

### 3.6 Trocas e devoluções

**Colunas:** loja, operador ou atendente, devoluções, valor, % sobre a venda, % sem cupom de origem, % em dinheiro, prazo médio entre venda e devolução.
**Sinais de atenção:** devolução sem venda de origem, devolução no mesmo dia e mesmo operador da venda, itens de alto valor recorrentes, cliente com muitas devoluções.
Complementa `../../analyze-mcp-vendas/references/relatorios.md`, 3.5, com o olhar de auditoria.
