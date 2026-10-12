# Índice de saúde do varejo (0 a 100)

Um número que resume a operação no período, sempre acompanhado da decomposição: quem vê o 62 precisa saber de onde ele veio em um olhar. O template calcula o índice a partir dos componentes declarados no config; esta página diz quais componentes usar e com quais limites.

## Como o cálculo funciona

Cada componente tem um valor `ruim` (vale 0 ponto) e um valor `bom` (vale 100 pontos). O valor medido vira pontos por interpolação linear e é limitado entre 0 e 100; isso funciona tanto para "quanto maior, melhor" (`ruim` < `bom`) quanto para "quanto menor, melhor" (`ruim` > `bom`). O índice é a média dos pontos ponderada pelos pesos **dos componentes que têm dado**: um componente sem dado sai da conta e o painel mostra "N de M componentes com dado".

Faixas: 70 ou mais **Saudável**, 50 a 69 **Atenção**, 30 a 49 **Risco**, abaixo de 30 **Crítico**. Sempre com ícone e rótulo, nunca só a cor.

## Componentes padrão

| Componente | Campo | Peso | Ruim (0) | Bom (100) | Por quê |
|---|---|---|---|---|---|
| Crescimento da venda | `cresc_venda_pct` | 25 | -10 | 10 | Variação da venda líquida contra o período anterior equivalente |
| Ticket médio | `var_ticket_pct` | 10 | -8 | 5 | Variação do ticket; cair mais rápido que a venda indica perda de cesta |
| Desconto sobre a venda bruta | `desconto_pct` | 15 | 8 | 2 | Desconto alto corrói margem; parte é promoção, parte é vazamento |
| Cancelamentos | `cancel_pct` | 15 | 3 | 0,5 | Cancelamento alto aponta problema de operação de caixa ou fraude |
| Margem bruta | `margem_pct` | 20 | 15 | 28 | Faixa típica do varejo alimentar; ajuste para o segmento |
| Clientes identificados | `ident_pct` | 15 | 10 | 50 | Base para CRM e fidelidade |

Os limites são referências de mercado, não verdade: são hipóteses para calibrar com o histórico do próprio varejista. Se o usuário der metas, use as metas como `bom`. Para outros segmentos, ajuste margem (farma, moda e material de construção têm faixas diferentes) e diga isso na leitura.

## Quando um componente fica fora

Deixe o campo `null` na linha do score (o componente sai da conta) quando:

- **Crescimento e ticket:** os períodos não são comparáveis (algum tem menos de 30 cupons, ou um tem menos de 10% dos cupons do outro).
- **Margem:** cobertura de custo abaixo de 90% da venda, ou dispersão entre departamentos abaixo de 1 p.p. (custo estimado).
- **Clientes identificados:** campo nunca preenchido no histórico inteiro; é falta de captura, não desempenho.
- **Qualquer um:** o campo não existe na base.

Com menos de 2 componentes com dado, não mostre o índice: um número feito de um só indicador engana mais do que informa. Liste o índice em `indisponiveis`.

## Consulta do score

Reaproveite a consulta de totalizadores (`indicadores-varejo.md`, 4.2) e calcule os componentes em volta dela, devolvendo `NULL` onde a regra mandar:

```sql
SELECT
  CASE WHEN comparavel = 1 THEN CAST(100.0*(venda_liquida - venda_liquida_ant)/NULLIF(venda_liquida_ant,0) AS float) END cresc_venda_pct,
  CASE WHEN comparavel = 1 THEN CAST(100.0*(ticket - ticket_ant)/NULLIF(ticket_ant,0) AS float) END var_ticket_pct,
  desconto_pct, cancel_pct
FROM (<consulta 4.2>) k
```

Margem e clientes identificados entram como colunas extras quando passarem nas regras acima; quando não passarem, omita o componente do config em vez de mandar `NULL` eternamente.
