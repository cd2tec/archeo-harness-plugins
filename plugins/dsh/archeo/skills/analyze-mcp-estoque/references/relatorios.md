# Estoque: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.8)

Consultas em SQL Server, com marcadores `<assim>` no lugar de tabelas e colunas. Traduza para outras engines com `../../spec-mcp-tool/references/regras-sql.md`, seção 1. São **[modelo]**: valem depois de rodar e passar na prova no banco conectado. O padrão de janela para acumulado é **[validado]** pelo conector.

## 1. Mapeamento

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Saldo | Estoque geral, ruptura, cobertura | `estoque`, `saldo`, `sld`, `qtd_estoque`, `posicao`, `stock` | Chave (produto + loja + depósito?), unidade, data de atualização, se há saldo reservado, em trânsito ou bloqueado |
| Movimento | Kardex, giro, posição retroativa | `movimento`, `mov_est`, `kardex`, `historico_estoque`, `lancamento` | Data, tipo de operação, quantidade, custo no movimento, documento e parceiro de origem |
| Tipo de operação | Sinal e nome do movimento | `tipo_mov`, `operacao`, `cod_oper`, `natureza`, `historico` | Quais entram, quais saem, quais são estorno |
| Inventário (lote) | Análise de balanço | `inventario`, `balanco`, `contagem`, `lote`, `congelado` | Cabeçalho (data, loja, situação) e itens (quantidade congelada, contada, custo) |
| Produto | Descrição, departamento, situação | `produto`, `mercadoria`, `item`, `sku` | Se o cadastro é por loja; flag de ativo, de fora de linha e de controla estoque |
| Mercadológico | Quebras do relatório | `departamento`, `secao`, `grupo`, `subgrupo`, `categoria`, `familia` | Níveis da árvore e chave |
| Fornecedor do produto | Filtro por fornecedor | `fornecedor`, `prod_fornec`, `fabricante` | Fornecedor principal, quando o produto tem vários |
| Custo e preço | Valorização | `custo`, `custo_medio`, `custo_reposicao`, `preco_venda` | Qual custo é (médio, última entrada), se é por loja, cobertura |
| Venda por item | Cobertura, ruptura, parado | (ver `build-mcp-dashboard`, mapeamento de itens vendidos) | Mesma unidade do saldo |

## 2. O que medir

- Saldo: linhas, itens com saldo > 0, = 0 e < 0, soma de quantidade, data mais recente de atualização.
- Movimento: linhas, primeira e última data, tabela por tipo de operação com contagem e soma de quantidade.
- Inventário: lotes por situação, data do último, itens por lote.
- Produto: ativos, inativos, sem departamento, sem custo.

```sql
SELECT m.<tipo_operacao>, COUNT(*) linhas,
       CAST(SUM(m.<quantidade>) AS float) qtd,
       CONVERT(varchar(10), MIN(m.<data>), 23) primeira, CONVERT(varchar(10), MAX(m.<data>), 23) ultima
FROM <movimento> m
GROUP BY m.<tipo_operacao>
ORDER BY COUNT(*) DESC OFFSET 0 ROWS
```

A partir dessa tabela e do cadastro de tipos, defina `<sinal>`: `CASE WHEN m.<tipo_operacao> IN (<entradas>) THEN 1 WHEN m.<tipo_operacao> IN (<saidas>) THEN -1 ELSE 0 END`. Tipo sem classificação segura: pergunte.

## 3. Relatórios

### 3.1 Estoque geral

**Pergunta:** quanto tenho, onde e quanto vale.

**Colunas (analítico):** loja, departamento, código, descrição, unidade, saldo, custo unitário, valor a custo, preço de venda, valor a venda, margem potencial %, data da última entrada e da última venda quando houver.
**Sintético:** por departamento (ou loja, fornecedor, segmento): itens com saldo, saldo, valor a custo, valor a venda, participação % no valor, itens negativos, itens zerados.

**Parâmetros naturais:** loja, departamento, fornecedor, situação do produto, só com saldo.

```sql
SELECT x.<cod_departamento>, d.<descricao> departamento,
       x.itens, x.itens_negativos, x.itens_zerados,
       CAST(x.valor_custo AS float) valor_custo, CAST(x.valor_venda AS float) valor_venda,
       CAST(100.0 * x.valor_custo / NULLIF(SUM(x.valor_custo) OVER (), 0) AS float) part_pct
FROM (SELECT p.<cod_departamento>,
             SUM(CASE WHEN s.<saldo> > 0 THEN 1 ELSE 0 END) itens,
             SUM(CASE WHEN s.<saldo> < 0 THEN 1 ELSE 0 END) itens_negativos,
             SUM(CASE WHEN s.<saldo> = 0 THEN 1 ELSE 0 END) itens_zerados,
             SUM(CASE WHEN s.<saldo> > 0 THEN s.<saldo> * COALESCE(s.<custo>, 0) ELSE 0 END) valor_custo,
             SUM(CASE WHEN s.<saldo> > 0 THEN s.<saldo> * COALESCE(s.<preco>, 0) ELSE 0 END) valor_venda
      FROM <saldo_estoque> s
      JOIN <produto> p ON p.<cod_produto> = s.<cod_produto> /* e loja, se o cadastro for por loja */
      WHERE s.<cod_loja> = COALESCE(NULLIF(<loja>, 0), s.<cod_loja>)
        AND p.<controla_estoque> = <sim>
      GROUP BY p.<cod_departamento>) x
LEFT JOIN <departamento> d ON d.<cod_departamento> = x.<cod_departamento>
ORDER BY x.valor_custo DESC OFFSET 0 ROWS
```

**Decisões a declarar:** saldo negativo fica fora do valor (somado à parte como inconsistência); qual custo foi usado; se saldo reservado ou em trânsito entrou.
**Prova:** soma de `valor_custo` do relatório = `SUM(saldo * custo)` direto na tabela de saldo com os mesmos filtros, sem join.
**Leituras típicas:** concentração do valor em poucos departamentos, itens negativos (saldo sem confiança), valor parado em itens inativos ou fora de linha, itens sem custo.

### 3.2 Kardex

**Pergunta:** como o produto chegou ao saldo atual.

**Colunas:** data, tipo de operação, documento, parceiro (fornecedor ou cliente), entrada, saída, saldo após o movimento, custo unitário, valor do movimento. Linha inicial com o saldo anterior ao período.

**Parâmetros naturais:** produto (obrigatório), loja, data inicial, data final.

```sql
SELECT CONVERT(varchar(10), k.dia, 23) data, k.tipo, k.documento, k.parceiro,
       CAST(k.entrada AS float) entrada, CAST(k.saida AS float) saida,
       CAST(k.saldo_anterior
            + SUM(k.entrada - k.saida) OVER (ORDER BY k.dia, k.seq ROWS UNBOUNDED PRECEDING) AS float) saldo,
       CAST(k.custo AS float) custo_unitario
FROM (SELECT m.<data> dia, m.<sequencial> seq, t.<descricao> tipo, m.<documento> documento, m.<parceiro> parceiro,
             CASE WHEN <sinal> =  1 THEN m.<quantidade> ELSE 0 END entrada,
             CASE WHEN <sinal> = -1 THEN m.<quantidade> ELSE 0 END saida,
             m.<custo> custo,
             (SELECT COALESCE(SUM(<sinal_a> * a.<quantidade>), 0)
              FROM <movimento> a
              WHERE a.<cod_produto> = m.<cod_produto> AND a.<cod_loja> = m.<cod_loja>
                AND a.<data> < '2025-07-01') saldo_anterior
      FROM <movimento> m
      LEFT JOIN <tipo_operacao> t ON t.<cod_tipo> = m.<tipo_operacao>
      WHERE m.<cod_produto> = <produto> AND m.<cod_loja> = <loja>
        AND m.<data> >= '2025-07-01' AND m.<data> < '2025-08-01') k
ORDER BY k.dia, k.seq OFFSET 0 ROWS
```

Notas:
- `seq` desempata movimentos do mesmo dia; sem uma coluna sequencial, use hora ou a chave da tabela. Sem desempate, o saldo linha a linha muda entre execuções.
- Se a tabela de movimento já grava o saldo após o movimento, use-o e confira contra o acumulado calculado: divergência entre os dois é achado.
- O saldo anterior recomposto desde o primeiro movimento só vale se o histórico estiver completo. Base com expurgo ou implantação com saldo inicial lançado direto: ancore no saldo atual e volte no tempo (3.8).
- Mais de uma loja: um Kardex por loja, ou consolidado com transferências internas somando zero.

**Prova:** saldo anterior + entradas - saídas = último saldo da lista; quando o período vai até a última data, último saldo = saldo atual da tabela de saldo.
**Leituras típicas:** ajustes manuais recorrentes, saída sem entrada que deixa o saldo negativo, entrada com custo muito fora da média, longos intervalos sem movimento.

### 3.3 Análise de lote de inventário

**Pergunta:** o que o balanço encontrou e quanto isso custa.

**Colunas (analítico):** código, descrição, departamento, quantidade congelada, quantidade contada, divergência (contada - congelada), custo unitário, divergência em valor, situação (sobra, falta, sem divergência, não contado).
**Sintético:** por departamento e total: itens no lote, contados, não contados, com divergência, sobras em valor, faltas em valor, divergência líquida, divergência absoluta, acuracidade em itens % e acuracidade em valor %.

**Parâmetros naturais:** lote (ou loja + data), departamento, só divergentes.

```sql
SELECT p.<cod_departamento>,
       COUNT(*) itens,
       SUM(CASE WHEN i.<qtd_contada> IS NULL THEN 1 ELSE 0 END) nao_contados,
       SUM(CASE WHEN i.<qtd_contada> <> i.<qtd_congelada> THEN 1 ELSE 0 END) divergentes,
       CAST(SUM(CASE WHEN i.<qtd_contada> > i.<qtd_congelada> THEN (i.<qtd_contada> - i.<qtd_congelada>) * COALESCE(i.<custo>, 0) ELSE 0 END) AS float) sobra_valor,
       CAST(SUM(CASE WHEN i.<qtd_contada> < i.<qtd_congelada> THEN (i.<qtd_congelada> - i.<qtd_contada>) * COALESCE(i.<custo>, 0) ELSE 0 END) AS float) falta_valor,
       CAST(SUM(i.<qtd_congelada> * COALESCE(i.<custo>, 0)) AS float) valor_congelado,
       CAST(100.0 * SUM(CASE WHEN i.<qtd_contada> = i.<qtd_congelada> THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN i.<qtd_contada> IS NOT NULL THEN 1 ELSE 0 END), 0) AS float) acuracidade_itens_pct
FROM <inventario_item> i
JOIN <produto> p ON p.<cod_produto> = i.<cod_produto>
WHERE i.<cod_lote> = <lote>
GROUP BY p.<cod_departamento>
ORDER BY falta_valor DESC OFFSET 0 ROWS
```

Definições (declare na entrega):
- **Acuracidade em itens** = itens contados sem divergência / itens contados.
- **Acuracidade em valor** = 1 - (sobras + faltas em valor) / valor congelado. Usa a divergência **absoluta**: sobra e falta não se compensam.
- **Divergência líquida** = sobras - faltas. É o que ajusta o resultado; a absoluta mede a qualidade do processo.
- **Não contado** é diferente de contado zero. Se o sistema grava zero nos dois casos, diga que não dá para separar.

**Prova:** itens do lote = contados + não contados; total em valor = soma do analítico.
**Leituras típicas:** falta concentrada em poucos itens de alto valor (furto, erro de recebimento), sobra e falta em itens parecidos (troca de código na contagem ou no caixa), muitos não contados (balanço incompleto), divergência em pesáveis (tara, quebra operacional).

### 3.4 Cobertura e ruptura

**Pergunta:** o que vai faltar, o que já faltou e o que está sobrando.

**Colunas:** código, descrição, departamento, saldo, venda média diária (quantidade vendida / dias com loja aberta no período), dias de cobertura (saldo / venda média diária), situação.

**Situações (limites default, ajustáveis):**
| Situação | Regra |
|---|---|
| Ruptura | Saldo <= 0, produto ativo e com venda nos últimos 30 dias |
| Risco | Cobertura abaixo de 3 dias |
| Saudável | De 3 a 45 dias |
| Excesso | Acima de 45 dias |
| Sem giro | Saldo > 0 e nenhuma venda no período (vai para 3.5) |

Perecíveis e itens de alto giro pedem limites menores: se o usuário disser o departamento, ajuste e declare.

```sql
SELECT s.<cod_produto>, CAST(s.<saldo> AS float) saldo,
       CAST(COALESCE(v.qtd, 0) / 30.0 AS float) venda_dia,
       CAST(s.<saldo> / NULLIF(COALESCE(v.qtd, 0) / 30.0, 0) AS float) dias_cobertura
FROM <saldo_estoque> s
LEFT JOIN (SELECT i.<cod_produto>, SUM(i.<quantidade>) qtd
           FROM <itens_venda> i
           WHERE <filtro_validos> AND i.<cod_loja> = <loja>
             AND i.<data> >= '2025-07-01' AND i.<data> < '2025-07-31'
           GROUP BY i.<cod_produto>) v ON v.<cod_produto> = s.<cod_produto>
WHERE s.<cod_loja> = <loja>
```

**Indicador de ruptura** = itens em ruptura / itens ativos do sortimento com venda recente. Diga sempre o denominador: ruptura sobre o cadastro inteiro fica artificialmente baixa.
**Limite da análise:** ruptura medida pelo saldo do sistema é a ruptura **contábil**. Produto com saldo no sistema e gôndola vazia (ruptura operacional) não aparece, e saldo negativo ou errado esconde ruptura real. Diga isso quando houver muitos negativos.
**Venda perdida estimada** (opcional, marque como estimativa): dias sem saldo x venda média diária x preço.
**Prova:** soma da quantidade vendida usada = quantidade vendida no período pela fonte de vendas.

### 3.5 Estoque sem venda

**Colunas:** código, descrição, departamento, saldo, valor a custo, última venda, dias sem venda, última entrada.
**Faixas:** 30 a 60, 61 a 90, 91 a 180, acima de 180 dias, e nunca vendeu.
Separe item novo (entrada recente, ainda sem venda) de item parado: sem isso, lançamento vira encalhe.
**Resumo:** valor parado por faixa e participação no estoque total.
**Leitura típica:** capital imobilizado, candidatos a remarcação, devolução ao fornecedor ou transferência entre lojas (parado em uma, vendendo em outra).

### 3.6 Inconsistências de saldo

Lista de exceções, cada uma com contagem e os 20 maiores casos:
- saldo negativo;
- saldo positivo em produto inativo ou fora de linha;
- produto que controla estoque, com venda no período, e sem nenhum movimento de entrada;
- saldo com custo zero ou nulo;
- saldo diferente do Kardex recomposto (amostra dos itens de maior valor, não a base inteira);
- quantidade fracionada em item vendido por unidade.

### 3.7 Giro e estoque médio

- **Giro** = custo da mercadoria vendida no período / estoque médio a custo.
- **Prazo médio de estoque (dias)** = dias do período / giro.
- **Estoque médio:** média das posições diárias ou mensais, se o ERP guardar fotografia; senão (posição inicial recomposta + posição final) / 2, dizendo que é aproximação de dois pontos.

Apresente por departamento, com o total. Giro calculado com venda a preço de venda sobre estoque a custo é erro comum: os dois lados a custo.

### 3.8 Posição retroativa

Saldo na data D = saldo atual - soma dos movimentos com sinal depois de D.

```sql
SELECT s.<cod_produto>,
       CAST(s.<saldo> - COALESCE(m.depois, 0) AS float) saldo_na_data
FROM <saldo_estoque> s
LEFT JOIN (SELECT a.<cod_produto>, SUM(<sinal_a> * a.<quantidade>) depois
           FROM <movimento> a
           WHERE a.<cod_loja> = <loja> AND a.<data> >= '2025-07-01'
           GROUP BY a.<cod_produto>) m ON m.<cod_produto> = s.<cod_produto>
WHERE s.<cod_loja> = <loja>
```

Prefira a fotografia do próprio ERP quando existir (tabela de posição diária ou de fechamento mensal). A valorização retroativa precisa do custo da época: com o custo atual, diga que a quantidade é da data e o custo é de hoje.
**Prova:** aplicar a mesma lógica com D = hoje devolve o saldo atual; e, para uma amostra, o resultado bate com o Kardex.
