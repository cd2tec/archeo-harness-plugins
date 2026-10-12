# Indicadores de varejo: mapeamento, consultas e gráficos

Conteúdo:
1. Mapeamento do ERP
2. Regras de consulta
3. Catálogo de seções (o que entra no painel, em que ordem)
4. Consultas-modelo

## 1. Mapeamento do ERP

ERPs e PDVs de varejo variam muito nos nomes, mas os domínios são sempre os mesmos. Procure com `db_search_columns` (ou `INFORMATION_SCHEMA.COLUMNS` com `LIKE`) usando os termos abaixo, em português e inglês, e confirme com uma amostra de poucas colunas.

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Venda por cupom | Totalizadores, linha do tempo, horário, operadores | `resumo_venda`, `venda`, `cupom`, `cupom_fiscal`, `nfce`, `movimento`, `pdv`, `ticket` | Coluna de valor líquido, data, hora, loja, operador; flags de cancelamento e registro indevido |
| Itens vendidos | Departamentos, produtos, curva ABC, margem | `item_vendido`, `venda_item`, `itens`, `det_venda`, `mov_item` | Valor do item, quantidade, código do produto e departamento, custo |
| Produto | Nome dos produtos | `mercadoria`, `produto`, `item`, `sku`, `descricao` | Chave (tipo e se é por loja), descrição |
| Departamento | Nome das categorias | `departamento`, `secao`, `categoria`, `grupo`, `familia` | Chave e se o cadastro é por loja |
| Loja | Ranking de lojas | `loja`, `filial`, `empresa`, `estabelecimento`, `unidade` | Quantas lojas têm movimento no período |
| Pagamento | Mix de meios de pagamento | `finalizadora`, `forma_pagamento`, `meio_pagamento`, `tender`, `recebimento` | Valor recebido, troco, código e descrição; registros que não são venda (sangria, suprimento, função de controle) |
| Custo | Margem | `custo`, `cmv`, `preco_custo`, `vlr_custo` | Cobertura (% da venda com custo > 0) e dispersão entre departamentos |
| Estoque | Ruptura, cobertura | `estoque`, `saldo`, `qtde_estoque`, `posicao_estoque` | Data da posição e se está atualizada |
| Cliente | Identificação, fidelidade | `cpf`, `cnpj`, `cpfcnpj`, `cliente`, `consumidor`, `fidelidade` | % de cupons com cliente preenchido ao longo do histórico |

Prefira **views de resumo do sistema** às tabelas cruas: costumam já unir formatos de documento (cupom antigo e NFC-e, por exemplo) e aplicar regras do fabricante. Quando houver view e tabela, compare os totais das duas num dia de movimento antes de escolher.

**Flags que quase sempre viram filtro fixo:** registro indevido, cancelado, estornado, excluído, inativo, documento de teste, função de controle (abertura e fechamento de caixa, sangria). Olhe os valores distintos e a soma por valor antes de decidir.

## 2. Regras de consulta

- **Sem CTE.** O conector pode recusar `WITH`. Use tabelas derivadas (`FROM (SELECT ...) x`).
- **`ORDER BY` só com `TOP` ou `OFFSET 0 ROWS`** (SQL Server); em outras engines, teste.
- **Valores com `CAST(... AS float)`** quando o conector devolver decimal codificado.
- **Datas como texto** (`CONVERT(varchar(10), d, 23)` no SQL Server, `to_char(d, 'YYYY-MM-DD')` no PostgreSQL e Oracle) para o template ler sem ambiguidade.
- **Período em uma tabela derivada `p`** com `ini`, `fim` (exclusivo) e `ant_ini`. O período anterior tem a mesma duração: `ant_ini = ini - (fim - ini)`. No modo ao vivo, `ini` e `fim` saem de `MAX(data)` da própria base (seção 4.1), para o painel andar sozinho.
- **Dia da semana sem depender de configuração da sessão:** no SQL Server, `(DATEDIFF(day, '19000107', data) % 7) + 1` dá 1 = domingo ... 7 = sábado (1900-01-07 foi um domingo). `DATEPART(weekday)` muda com `DATEFIRST`.
- **Cadastros por loja.** Junte pelo código **e pela loja**; um join só pelo código multiplica os valores (uma linha por loja no cadastro) e pode trazer o nome de outra loja. Veja 4.5.
- **Reconcilie** cada seção que reparte a venda com a venda total (tolerância de 2%).

## 3. Catálogo de seções

Ordem no painel: o resumo antes do detalhe. Omita a seção quando a regra de omissão disser; liste-a em `indisponiveis` com o motivo.

| # | Seção | Tipo no config | Largura | Dado | Omitir quando |
|---|---|---|---|---|---|
| 1 | Totalizadores | `kpis` | (faixa do topo) | Venda por cupom | Nunca; sem venda não há painel |
| 2 | Índice de saúde | `score` | (faixa do topo) | Saída dos totalizadores | Menos de 2 componentes com dado |
| 3 | Venda por dia | `linha` | inteira | Venda por cupom | Período de 1 dia (use o heatmap) |
| 4 | Venda por dia da semana e hora | `heatmap` | metade | Venda por cupom com hora | Hora não capturada |
| 5 | Meios de pagamento | `barras` com `participacao` | metade | Pagamento | Não reconcilia com a venda |
| 6 | Departamentos | `barras` com `participacao` | metade | Itens + departamento | Menos de 3 departamentos |
| 7 | Produtos mais vendidos | `barras` | metade | Itens + produto | Sem descrição de produto e sem código legível |
| 8 | Lojas | `barras` com `var_pct` | inteira | Venda por loja | Menos de 3 lojas com movimento (diga no cabeçalho quantas são) |
| 9 | Operadores: descontos e cancelamentos | `tabela` | inteira | Venda por cupom com operador | Sem operador; ou desconto e cancelamento zerados |
| 10 | Concentração do sortimento (curva ABC) | `tabela` | metade | Itens | Menos de 20 SKUs vendidos |
| 11 | Estoque: ruptura e cobertura | `kpis` ou `tabela` | metade | Estoque + venda | Posição de estoque com mais de 7 dias ou sem data |

### Totalizadores (cards)

| Card | Campo | Formato | Melhor | Regra |
|---|---|---|---|---|
| Venda líquida | `venda_liquida` | moeda | alta | Sempre |
| Cupons | `cupons` | inteiro | alta | Sempre |
| Ticket médio | `ticket` | moeda | alta | Sempre |
| Itens por cupom | `itens_cupom` | decimal | alta | Quando quantidade de itens existir |
| Desconto sobre a venda bruta | `desconto_pct` | pct | baixa | Quando houver campo de desconto |
| Cancelamentos sobre a venda | `cancel_pct` | pct | baixa | Quando houver valor cancelado |
| Margem bruta | `margem_pct` | pct | alta | Custo com cobertura acima de 90% da venda; se a dispersão entre departamentos for menor que 1 p.p., mostre com `nota: "custo estimado"` e sem comparação |
| Clientes identificados | `ident_pct` | pct | alta | Quando o campo de cliente tiver sido preenchido em algum momento do histórico |

Cada card de comparação recebe o campo `<campo>_ant`. A seção usa `campoComparavel: "comparavel"`, um campo 0 ou 1 calculado na consulta (1 quando os dois períodos têm pelo menos 30 cupons e nenhum tem menos de 10% dos cupons do outro).

## 4. Consultas-modelo

Escritas e validadas em SQL Server. Troque `<venda>`, `<itens>` e os nomes de coluna pelos do banco mapeado; traduza a sintaxe para outras engines com `regras-sql.md`, seção 1. Onde aparece `'2025-07-01'` e `'2025-09-01'`, vão o início e o fim (exclusivo) do período.

### 4.1 Período no modo ao vivo

Substitui a tabela derivada de datas fixas: últimos 30 dias até a última data com venda.

```sql
(SELECT DATEADD(day, -29, mx) ini, DATEADD(day, 1, mx) fim
 FROM (SELECT CAST(MAX(dta_movimento) AS date) mx FROM <venda> WHERE <filtro_validos>) m) r0
```

### 4.2 Totalizadores (atual e anterior numa linha)

```sql
SELECT
  CAST(SUM(CASE WHEN atual=1 THEN liq ELSE 0 END) AS float) venda_liquida,
  CAST(SUM(CASE WHEN atual=0 THEN liq ELSE 0 END) AS float) venda_liquida_ant,
  SUM(atual) cupons, SUM(1-atual) cupons_ant,
  CAST(SUM(CASE WHEN atual=1 THEN liq ELSE 0 END)/NULLIF(SUM(atual),0) AS float) ticket,
  CAST(SUM(CASE WHEN atual=0 THEN liq ELSE 0 END)/NULLIF(SUM(1-atual),0) AS float) ticket_ant,
  CAST(SUM(CASE WHEN atual=1 THEN itens ELSE 0 END)/NULLIF(SUM(atual),0) AS float) itens_cupom,
  CAST(SUM(CASE WHEN atual=0 THEN itens ELSE 0 END)/NULLIF(SUM(1-atual),0) AS float) itens_cupom_ant,
  CAST(100.0*SUM(CASE WHEN atual=1 THEN des ELSE 0 END)/NULLIF(SUM(CASE WHEN atual=1 THEN liq+des-acr ELSE 0 END),0) AS float) desconto_pct,
  CAST(100.0*SUM(CASE WHEN atual=0 THEN des ELSE 0 END)/NULLIF(SUM(CASE WHEN atual=0 THEN liq+des-acr ELSE 0 END),0) AS float) desconto_pct_ant,
  CAST(100.0*SUM(CASE WHEN atual=1 THEN canc ELSE 0 END)/NULLIF(SUM(CASE WHEN atual=1 THEN liq+des-acr+canc ELSE 0 END),0) AS float) cancel_pct,
  CAST(100.0*SUM(CASE WHEN atual=0 THEN canc ELSE 0 END)/NULLIF(SUM(CASE WHEN atual=0 THEN liq+des-acr+canc ELSE 0 END),0) AS float) cancel_pct_ant,
  CASE WHEN SUM(atual) >= 30 AND SUM(1-atual) >= 30 AND SUM(1-atual) >= 0.1*SUM(atual) AND SUM(atual) >= 0.1*SUM(1-atual) THEN 1 ELSE 0 END comparavel,
  CONVERT(varchar(10), MIN(ini), 23) periodo_ini,
  CONVERT(varchar(10), DATEADD(day,-1,MIN(fim)), 23) periodo_fim,
  CONVERT(varchar(10), MIN(ant_ini), 23) anterior_ini,
  CONVERT(varchar(10), DATEADD(day,-1,MIN(ini)), 23) anterior_fim
FROM (
  SELECT p.ini, p.fim, p.ant_ini,
         CASE WHEN v.dta_movimento >= p.ini THEN 1 ELSE 0 END atual,
         v.vlr_total_venda liq, COALESCE(v.vlr_descontos,0) des, COALESCE(v.vlr_acrescimos,0) acr,
         COALESCE(v.vlr_cancelamentos,0) canc, COALESCE(v.qtde_vendida,0) itens
  FROM <venda> v
  CROSS JOIN (SELECT ini, fim, DATEADD(day, -DATEDIFF(day, ini, fim), ini) ant_ini
              FROM (SELECT CAST('2025-07-01' AS date) ini, CAST('2025-09-01' AS date) fim) r0) p
  WHERE <filtro_validos> AND v.dta_movimento >= p.ant_ini AND v.dta_movimento < p.fim
) b
```

Os campos `periodo_*` e `anterior_*` alimentam o cabeçalho: use `metaSecao` apontando para esta seção.

### 4.3 Venda por dia (atual alinhado com anterior)

```sql
SELECT CONVERT(varchar(10), DATEADD(day, d.dia, MIN(d.ini)), 23) x,
       CAST(SUM(CASE WHEN d.atual=1 THEN d.liq END) AS float) atual,
       CAST(SUM(CASE WHEN d.atual=0 THEN d.liq END) AS float) anterior
FROM (
  SELECT p.ini, CASE WHEN v.dta_movimento >= p.ini THEN 1 ELSE 0 END atual,
         CASE WHEN v.dta_movimento >= p.ini THEN DATEDIFF(day, p.ini, v.dta_movimento)
              ELSE DATEDIFF(day, p.ant_ini, v.dta_movimento) END dia,
         v.vlr_total_venda liq
  FROM <venda> v CROSS JOIN (<tabela derivada p de 4.2>) p
  WHERE <filtro_validos> AND v.dta_movimento >= p.ant_ini AND v.dta_movimento < p.fim
) d
GROUP BY d.dia ORDER BY d.dia OFFSET 0 ROWS
```

Dias sem venda não voltam da consulta; `preencherDias: true` na seção completa com zero entre `periodo_ini` e `periodo_fim`.

### 4.4 Dia da semana x hora

```sql
SELECT (DATEDIFF(day, '19000107', v.dta_movimento) % 7) + 1 dia,
       v.hora_venda / 10000 hora,
       CAST(SUM(v.vlr_total_venda) AS float) valor
FROM <venda> v
WHERE <filtro_validos> AND v.dta_movimento >= <ini> AND v.dta_movimento < <fim>
GROUP BY (DATEDIFF(day, '19000107', v.dta_movimento) % 7) + 1, v.hora_venda / 10000
```

Confira o formato da hora numa amostra (HHMM, HHMMSS, datetime) antes de dividir.

### 4.5 Ranking com rótulo de cadastro (departamentos, produtos, pagamentos)

Resolva o nome **por loja** e agrupe pelo nome resolvido: em muitos ERPs o mesmo código significa coisas diferentes em cada loja (o departamento 13 pode ser "Perfumaria" numa loja e "Têxtil" em outra), e agregar o cadastro sem a loja troca os nomes sem dar erro. O segundo join é o fallback para lojas sem cadastro próprio.

```sql
SELECT TOP 10 rotulo, CAST(SUM(valor) AS float) valor
FROM (SELECT COALESCE(cl.descricao, cg.descricao, 'Código ' + CAST(i.<cod> AS varchar(20))) rotulo, i.<valor> valor
      FROM <itens> i
      LEFT JOIN <cadastro> cl ON cl.<cod> = i.<cod> AND cl.cod_loja = i.cod_loja
      LEFT JOIN (SELECT <cod>, MAX(descricao) descricao FROM <cadastro> GROUP BY <cod>) cg ON cg.<cod> = i.<cod>
      WHERE <filtro_validos> AND i.dta_movimento >= <ini> AND i.dta_movimento < <fim>) x
GROUP BY rotulo ORDER BY valor DESC
```

Se o cadastro tiver mais de uma linha por (código, loja), o primeiro join também multiplica: agregue-o por (código, loja) antes. Pagamento: valor = recebido menos troco, sem as funções que não são venda. Rode uma vez sem `TOP` e confira se a soma bate com a venda líquida; mostre as 8 maiores e some o resto em "Outros".

### 4.6 Lojas com variação

```sql
SELECT 'Loja ' + CAST(cod_loja AS varchar(10)) rotulo,
       CAST(SUM(CASE WHEN atual=1 THEN liq ELSE 0 END) AS float) valor,
       CAST(100.0*(SUM(CASE WHEN atual=1 THEN liq ELSE 0 END) - SUM(CASE WHEN atual=0 THEN liq ELSE 0 END))
            / NULLIF(SUM(CASE WHEN atual=0 THEN liq ELSE 0 END),0) AS float) var_pct
FROM (<mesma base de 4.2, com cod_loja>) b
GROUP BY cod_loja ORDER BY valor DESC OFFSET 0 ROWS
```

### 4.7 Operadores (descontos e cancelamentos)

```sql
SELECT TOP 10 'Operador ' + CAST(v.cod_operador AS varchar(10)) operador, COUNT(*) cupons,
       CAST(SUM(v.vlr_total_venda) AS float) venda,
       CAST(SUM(COALESCE(v.vlr_descontos,0)) AS float) descontos,
       CAST(100.0*SUM(COALESCE(v.vlr_descontos,0))/NULLIF(SUM(v.vlr_total_venda+COALESCE(v.vlr_descontos,0)),0) AS float) desconto_pct,
       CAST(SUM(COALESCE(v.vlr_cancelamentos,0)) AS float) cancelamentos
FROM <venda> v
WHERE <filtro_validos> AND v.dta_movimento >= <ini> AND v.dta_movimento < <fim>
GROUP BY v.cod_operador HAVING COUNT(*) >= 10
ORDER BY descontos DESC
```

`HAVING COUNT(*) >= 10` tira operadores de teste e treinamento do topo. Na leitura, aponte o operador com desconto percentual muito acima da média, não só o maior em reais.

### 4.8 Curva ABC

```sql
SELECT classe, COUNT(*) skus, CAST(100.0*COUNT(*)/MAX(n) AS float) skus_pct,
       CAST(100.0*SUM(valor)/MAX(total) AS float) venda_pct
FROM (SELECT valor, total, n,
             CASE WHEN acum - valor < 0.8*total THEN 'A' WHEN acum - valor < 0.95*total THEN 'B' ELSE 'C' END classe
      FROM (SELECT x.valor,
                   SUM(x.valor) OVER (ORDER BY x.valor DESC, x.cod ROWS UNBOUNDED PRECEDING) acum,
                   SUM(x.valor) OVER () total, COUNT(*) OVER () n
            FROM (SELECT i.<cod_produto> cod, SUM(i.<valor>) valor FROM <itens> i
                  WHERE <filtro_validos> AND i.dta_movimento >= <ini> AND i.dta_movimento < <fim>
                  GROUP BY i.<cod_produto>) x) y) z
GROUP BY classe ORDER BY classe OFFSET 0 ROWS
```

### 4.9 Margem e qualidade do custo

```sql
SELECT CAST(100.0*(SUM(valor)-SUM(custo))/NULLIF(SUM(valor),0) AS float) margem_pct,
       CAST(100.0*SUM(CASE WHEN custo > 0 THEN valor ELSE 0 END)/NULLIF(SUM(valor),0) AS float) cobertura_custo_pct,
       CAST(MAX(m) - MIN(m) AS float) dispersao_pp
FROM (SELECT <cod_departamento> d, SUM(<valor>) valor, SUM(COALESCE(<custo>,0)) custo,
             100.0*(SUM(<valor>)-SUM(COALESCE(<custo>,0)))/NULLIF(SUM(<valor>),0) m
      FROM <itens> WHERE <filtro_validos> AND dta_movimento >= <ini> AND dta_movimento < <fim>
      GROUP BY <cod_departamento> HAVING SUM(<valor>) > 100) x
```

Cobertura abaixo de 90%: sem margem no painel. Dispersão abaixo de 1 p.p.: custo estimado, mostre com nota e fora do índice.
