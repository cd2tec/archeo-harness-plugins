# Vendas: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.6)

Consultas em SQL Server com marcadores `<assim>`; **[modelo]** até passarem na prova no banco conectado. O padrão de participação e acumulado por janela é **[validado]** pelo conector.

## 1. Mapeamento

Venda por cupom, itens, produto, departamento, loja e custo: `../../build-mcp-dashboard/references/indicadores-varejo.md`, seção 1. Acrescente:

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Pedido e faturamento | Venda em atacado e distribuição | `pedido`, `pedido_venda`, `nota_saida`, `nf_saida`, `faturamento`, `romaneio` | Situação do pedido, data de emissão x faturamento x entrega, tipo de operação (venda, bonificação, remessa) |
| Cliente | Ranking, carteira | `cliente`, `pessoa`, `parceiro`, `consumidor` | Chave, tipo (PF ou PJ), situação, data de cadastro |
| Segmento e canal | Quebras | `segmento`, `ramo`, `atividade`, `canal`, `tipo_cliente`, `rede`, `grupo_cliente` | Onde fica (cliente, pedido, tabela de preço) e % preenchido |
| Vendedor | Quebra comercial | `vendedor`, `representante`, `rca`, `supervisor`, `equipe` | Hierarquia e se o vendedor vem do pedido ou da carteira |
| Devolução | Venda líquida, motivos | `devolucao`, `troca`, `motivo_dev`, `nf_entrada` com operação de devolução | Vínculo com a venda original, motivo |
| Composição | Produto final x componentes | `composicao`, `receita`, `ficha_tecnica`, `kit`, `estrutura`, `componente`, `rendimento`, `producao` | Quantidade do componente por unidade do pai, perda prevista, se a venda baixa o pai ou os componentes |

## 2. O que medir

- Venda: período com dado, linhas por tipo de operação e por situação, % com cliente identificado, % com segmento e vendedor.
- Bonificação, remessa, transferência e venda para consumo interno costumam estar na mesma tabela: separe pelo tipo de operação ou CFOP (Código Fiscal de Operações e Prestações) antes de somar.
- Devolução: volume, período, % com vínculo à venda original e % com motivo.
- Composição: quantos produtos têm ficha, quantos componentes por ficha, fichas com componente inativo.

## 3. Relatórios

### 3.1 ABC de venda

**Colunas:** posição, código, descrição (produto, cliente, segmento ou vendedor), quantidade, venda líquida, participação %, acumulado %, classe; com custo confiável, margem em valor e %.
**Quadro de classes:** classe, itens, % dos itens, venda, % da venda.
**Parâmetros naturais:** período, loja, departamento ou segmento, dimensão, medida.

```sql
SELECT y.codigo, y.descricao, CAST(y.qtd AS float) qtd, CAST(y.valor AS float) valor,
       CAST(100.0 * y.valor / NULLIF(y.total, 0) AS float) part_pct,
       CAST(100.0 * y.acum / NULLIF(y.total, 0) AS float) acum_pct,
       CASE WHEN 100.0 * (y.acum - y.valor) / NULLIF(y.total, 0) < 80 THEN 'A'
            WHEN 100.0 * (y.acum - y.valor) / NULLIF(y.total, 0) < 95 THEN 'B' ELSE 'C' END classe
FROM (SELECT x.codigo, x.descricao, x.qtd, x.valor,
             SUM(x.valor) OVER () total,
             SUM(x.valor) OVER (ORDER BY x.valor DESC, x.codigo ROWS UNBOUNDED PRECEDING) acum
      FROM (SELECT i.<cod_produto> codigo, MAX(p.<descricao>) descricao,
                   SUM(i.<quantidade>) qtd, SUM(i.<valor_liquido>) valor
            FROM <itens_venda> i
            LEFT JOIN <produto> p ON p.<cod_produto> = i.<cod_produto> /* e loja, se o cadastro for por loja */
            WHERE <filtro_validos>
              AND i.<data> >= '2025-07-01' AND i.<data> < '2025-10-01'
            GROUP BY i.<cod_produto>
            HAVING SUM(i.<valor_liquido>) > 0) x) y
ORDER BY y.valor DESC, y.codigo OFFSET 0 ROWS
```

Notas:
- A classe usa o acumulado **antes** do item (`acum - valor`), para o item que cruza os 80% ainda ser A. É a convenção mais comum; declare.
- Itens com venda líquida zero ou negativa (devolução maior que a venda) ficam fora da curva e são contados à parte.
- A lista completa costuma passar de 30 linhas: quadro de classes e os 30 primeiros na conversa, o restante em planilha.
- ABC por margem: troque `valor` pela margem em valor e trate margem negativa à parte (ela distorce o acumulado).

**Prova:** soma de `valor` = venda líquida total do período pelos mesmos filtros; último `acum_pct` = 100.
**Leituras típicas:** quantos itens fazem a classe A e se estão com estoque (cruze com `analyze-mcp-estoque`, cobertura), cauda C longa com custo de manter em linha, item A com margem baixa, dependência de poucos clientes.

### 3.2 Venda por cliente e segmento

**Colunas (sintético por segmento):** segmento, clientes ativos, pedidos ou cupons, venda líquida, participação %, ticket médio, margem % (se confiável), variação contra o período anterior.
**Analítico por cliente:** cliente, segmento, vendedor, pedidos, venda, ticket, itens distintos comprados, última compra, margem %.
**Opcional:** cliente x departamento (mix), para ver o que cada cliente não compra.

```sql
SELECT c.<segmento>, COUNT(DISTINCT v.<cod_cliente>) clientes, COUNT(*) documentos,
       CAST(SUM(v.<valor_liquido>) AS float) venda,
       CAST(SUM(v.<valor_liquido>) / NULLIF(COUNT(*), 0) AS float) ticket
FROM <venda> v
LEFT JOIN <cliente> c ON c.<cod_cliente> = v.<cod_cliente>
WHERE <filtro_validos> AND v.<data> >= '2025-07-01' AND v.<data> < '2025-08-01'
GROUP BY c.<segmento>
ORDER BY SUM(v.<valor_liquido>) DESC OFFSET 0 ROWS
```

Mantenha a linha de "sem cliente" e a de "sem segmento": elas são o tamanho do que o relatório não enxerga.
**Prova:** soma das linhas = venda total; venda identificada + não identificada = total.
**Leituras típicas:** concentração (os 10 maiores clientes fazem quanto), segmento com ticket alto e margem baixa, clientes com mix estreito.

### 3.3 Produto final x componentes

**Pergunta:** quanto rendeu o produto composto e o que os componentes custaram.

Três casos, com tabelas diferentes:
| Caso | Exemplo | O que comparar |
|---|---|---|
| Kit ou cesta | Cesta de Natal | Receita do kit x soma dos componentes a preço e a custo |
| Receita ou produção | Pão, prato pronto | Custo da ficha técnica x custo real dos insumos baixados; rendimento previsto x obtido |
| Desmontagem | Carcaça em cortes | Peso de entrada x soma dos cortes; perda; custo rateado por corte |

**Colunas:** produto final, quantidade vendida ou produzida, receita, componente, quantidade prevista (ficha x quantidade do pai), quantidade real baixada (se houver apontamento), custo do componente, custo total, rendimento % (obtido / previsto), margem do produto final.

```sql
SELECT f.<cod_produto_final>, f.<cod_componente>, MAX(pc.<descricao>) componente,
       CAST(SUM(v.qtd * f.<qtd_por_unidade>) AS float) qtd_prevista,
       CAST(SUM(v.qtd * f.<qtd_por_unidade> * COALESCE(pc.<custo>, 0)) AS float) custo_previsto
FROM (SELECT i.<cod_produto> cod, SUM(i.<quantidade>) qtd
      FROM <itens_venda> i
      WHERE <filtro_validos> AND i.<data> >= '2025-07-01' AND i.<data> < '2025-08-01'
      GROUP BY i.<cod_produto>) v
JOIN <composicao> f ON f.<cod_produto_final> = v.cod
JOIN <produto> pc ON pc.<cod_produto> = f.<cod_componente>
GROUP BY f.<cod_produto_final>, f.<cod_componente>
ORDER BY f.<cod_produto_final>, custo_previsto DESC OFFSET 0 ROWS
```

Atenção: ficha com vários níveis (componente que também é composto) exige explodir nível a nível; sem CTE recursiva pelo conector, limite a dois ou três níveis com joins encadeados e diga quando houver nível não explodido.
**Prova:** custo previsto dos componentes / quantidade vendida = custo unitário do produto final no cadastro, ou a diferença é explicada (ficha desatualizada, perda).
**Leituras típicas:** produto final vendido abaixo do custo dos componentes, ficha desatualizada, rendimento real abaixo do previsto.

### 3.4 Comparativo de períodos

**Colunas:** dimensão (loja, departamento, segmento), venda atual, venda anterior, variação em valor e %, contribuição para a variação total em pontos percentuais.
- Período anterior: imediatamente anterior de mesma duração, ou mesmo período do ano anterior alinhado por dia da semana (364 dias atrás) quando houver histórico.
- **Mesmas lojas:** só lojas com venda nos dois períodos.
- Decomposição simples da variação, quando houver cupons: efeito fluxo (cupons) e efeito ticket.
- Use a regra de base comparável de `build-mcp-dashboard` (menos de 30 documentos ou menos de 10% do outro período: sem comparação).

**Prova:** total = mesmas lojas + novas + encerradas, nos dois períodos.

### 3.5 Devoluções e cancelamentos

**Colunas:** motivo, ocorrências, valor, % sobre a venda bruta; por produto, cliente, vendedor ou operador nos 20 maiores.
**Indicadores:** taxa de devolução (devolução / venda bruta), prazo médio entre venda e devolução (com vínculo), % sem motivo.
Separe cancelamento (antes de faturar ou no caixa) de devolução (depois da venda concluída) e de troca (devolução com nova venda).
**Prova:** soma por motivo = devolução total do período.
**Leituras típicas:** produto com devolução acima da média (qualidade, cadastro, entrega), concentração em um operador ou vendedor, motivo "outros" dominante (o campo não informa nada).

### 3.6 Carteira de clientes

**Positivação:** clientes com compra no período / clientes ativos da carteira (por vendedor ou segmento).
**RFV (Recência, Frequência e Valor; em inglês RFM, Recency, Frequency, Monetary):** dias desde a última compra, número de compras e valor em 12 meses, por cliente.
**Inativos:** compraram entre 90 e 365 dias atrás e não nos últimos 90 (limites ajustáveis), ordenados pelo valor que compravam.

```sql
SELECT v.<cod_cliente>, COUNT(*) compras, CAST(SUM(v.<valor_liquido>) AS float) valor,
       CONVERT(varchar(10), MAX(v.<data>), 23) ultima_compra,
       DATEDIFF(day, MAX(v.<data>), <data_referencia>) dias_sem_compra
FROM <venda> v
WHERE <filtro_validos> AND v.<cod_cliente> IS NOT NULL
  AND v.<data> >= DATEADD(day, -365, <data_referencia>)
GROUP BY v.<cod_cliente>
HAVING MAX(v.<data>) < DATEADD(day, -90, <data_referencia>)
ORDER BY SUM(v.<valor_liquido>) DESC OFFSET 0 ROWS
```

`<data_referencia>` é a última data com venda, não a data de hoje.
**Limite:** vale para a parcela identificada da venda; informe a cobertura. Sem contato nem endereço na saída (método comum, seção 6).
