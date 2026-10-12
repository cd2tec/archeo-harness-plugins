# Exemplo de ficha: pdv_venda_resumo_loja_mes

Exemplo ilustrativo sobre um banco fictício de varejo (`loja_demo`, SQL Server). Nomes de tabelas, colunas e números são inventados para mostrar o formato e o nível de detalhe esperados. Em um banco real, as regras de negócio saem da exploração do banco conectado.

**Banco:** loja_demo (SQL Server 16.0), via conector Archeo.

## Campos do formulário

| Campo | Valor |
|---|---|
| Nome técnico | `pdv_venda_resumo_loja_mes` |
| Nome de exibição | `Venda por loja e mês` |
| Schema | `dbo` |
| Descrição | `Venda bruta, descontos, acréscimos, venda líquida, cupons e ticket médio por loja e mês, sem cupons cancelados. Bruta = líquida + descontos - acréscimos. $1 = data inicial inclusiva (AAAA-MM-DD), $2 = data final exclusiva (AAAA-MM-DD; para julho/2025 inteiro use 2025-07-01 e 2025-08-01), $3 = código da loja (0 = todas). Para total por loja ou geral, some as linhas.` |

## SQL

```sql
SELECT
    v.cod_loja,
    YEAR(v.dt_movimento)  AS ano,
    MONTH(v.dt_movimento) AS mes,
    COUNT(*)              AS cupons,
    CAST(ROUND(SUM(v.vlr_liquido
                   + COALESCE(v.vlr_desconto, 0)
                   - COALESCE(v.vlr_acrescimo, 0)), 2) AS float) AS venda_bruta,
    CAST(ROUND(SUM(COALESCE(v.vlr_desconto, 0)), 2)  AS float) AS descontos,
    CAST(ROUND(SUM(COALESCE(v.vlr_acrescimo, 0)), 2) AS float) AS acrescimos,
    CAST(ROUND(SUM(v.vlr_liquido), 2)                AS float) AS venda_liquida,
    CAST(ROUND(SUM(v.vlr_liquido) / NULLIF(COUNT(*), 0), 2) AS float) AS ticket_medio
FROM vw_vendas_resumo v
WHERE v.flg_cancelado = 0
  AND v.dt_movimento >= CAST($1 AS date)
  AND v.dt_movimento <  CAST($2 AS date)
  AND v.cod_loja = COALESCE(NULLIF($3, 0), v.cod_loja)
GROUP BY v.cod_loja, YEAR(v.dt_movimento), MONTH(v.dt_movimento)
ORDER BY ano, mes, v.cod_loja
OFFSET 0 ROWS
```

## Parâmetros

| Posição | Nome | Tipo | Obrigatório | Exemplo |
|---|---|---|---|---|
| `$1` | `data_ini` | date | sim | `2025-07-01` |
| `$2` | `data_fim` | date | sim | `2025-09-01` |
| `$3` | `cod_loja` | integer | sim (0 = todas) | `0` |

## Limites

| Linhas | Bytes | Timeout (ms) |
|---|---|---|
| 500 | 1000000 | 5000 |

O resultado é lojas x meses e cabe folgado em 500 linhas. Com anos de movimento e sem índice em `dt_movimento`, suba o timeout para 15000.

## Teste após salvar

`$1 = 2025-07-01`, `$2 = 2025-09-01`, `$3 = 0` deve retornar (valores ilustrativos):

| cod_loja | ano | mes | cupons | venda_bruta | descontos | venda_liquida | ticket_medio |
|---|---|---|---|---|---|---|---|
| 1 | 2025 | 7 | 1.240 | 98.410,00 | 3.120,50 | 95.289,50 | 76,85 |
| 2 | 2025 | 7 | 860 | 61.300,20 | 1.050,00 | 60.250,20 | 70,06 |
| 1 | 2025 | 8 | 1.198 | 94.880,40 | 2.940,10 | 91.940,30 | 76,74 |
| 2 | 2025 | 8 | 902 | 64.020,00 | 1.210,80 | 62.809,20 | 69,63 |

## Premissas e pontos de atenção

- Fonte: `vw_vendas_resumo`, view do próprio sistema que já consolida os cupons. A exploração mostrou que as tabelas cruas exigiriam juntar dois formatos de cupom.
- `flg_cancelado = 0` exclui cupons cancelados; sem ele a venda fica inflada.
- `vlr_acrescimo` aceita NULL, por isso o `COALESCE` dentro da soma composta.
- `vlr_liquido` é o valor líquido; a venda bruta é calculada.
- `OFFSET 0 ROWS` e `CAST AS float` são ajustes de compatibilidade do conector (`regras-sql.md`, seção 4).
