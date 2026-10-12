# Preço, margem e promoção: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.6)

Consultas em SQL Server com marcadores `<assim>`; **[modelo]** até passarem na prova no banco conectado.

## 1. Mapeamento

Itens vendidos, produto, departamento e custo: `../../build-mcp-dashboard/references/indicadores-varejo.md`, seção 1. Acrescente:

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Preço vigente | Margem de cadastro, conferência | `preco`, `preco_venda`, `tabela_preco`, `prc`, `vlr_venda` | Chave (produto + loja + embalagem?), vigência, preço de atacado |
| Histórico de preço | Alterações | `historico_preco`, `alteracao_preco`, `log_preco`, `auditoria` | Data, preço anterior e novo, usuário, motivo |
| Promoção | Resultado de oferta | `promocao`, `oferta`, `encarte`, `campanha`, `preco_oferta`, `desconto_item` | Vigência, lojas, preço promocional, tipo; marca no item vendido |
| Custo no item vendido | Margem do período | `custo`, `cmv`, `vlr_custo` na tabela de itens | Se é gravado na venda (custo da época) |
| Impostos por item | Margem de contribuição | `icms`, `pis`, `cofins`, `aliquota`, `tributacao` | Valor por item ou só alíquota no cadastro |

## 2. O que medir

- Teste do custo (cobertura, dispersão, época do custo): SKILL.md, "Antes de qualquer margem".
- Preço: quantos preços por produto (lojas, embalagens, tabelas), % de itens ativos sem preço.
- Histórico de preço: existe? Desde quando? Guarda usuário e motivo?
- Promoção: quantas no período, com vigência e lojas; % dos itens vendidos marcados como promoção.
- Item vendido: o valor unitário é antes ou depois do desconto? Há coluna de desconto por item?

## 3. Relatórios

### 3.1 Margem

**Colunas (sintético por departamento):** departamento, venda líquida, custo, contribuição em valor, margem %, participação na venda %, participação na contribuição %, variação da margem em pontos percentuais contra o período anterior.
**Analítico:** produto, quantidade, preço médio praticado, custo médio unitário, margem %, contribuição.

```sql
SELECT x.d, MAX(dp.<descricao>) departamento,
       CAST(x.venda AS float) venda, CAST(x.custo AS float) custo,
       CAST(x.venda - x.custo AS float) contribuicao,
       CAST(100.0 * (x.venda - x.custo) / NULLIF(x.venda, 0) AS float) margem_pct,
       CAST(100.0 * x.venda / NULLIF(SUM(x.venda) OVER (), 0) AS float) part_venda_pct,
       CAST(100.0 * (x.venda - x.custo) / NULLIF(SUM(x.venda - x.custo) OVER (), 0) AS float) part_contrib_pct
FROM (SELECT i.<cod_departamento> d, SUM(i.<valor_liquido>) venda,
             SUM(COALESCE(i.<custo_unitario>, 0) * i.<quantidade>) custo
      FROM <itens_venda> i
      WHERE <filtro_validos> AND i.<data> >= '2025-07-01' AND i.<data> < '2025-08-01'
        AND COALESCE(i.<custo_unitario>, 0) > 0
      GROUP BY i.<cod_departamento>) x
LEFT JOIN <departamento> dp ON dp.<cod_departamento> = x.d
GROUP BY x.d, x.venda, x.custo
ORDER BY x.venda - x.custo DESC OFFSET 0 ROWS
```

Confirme se a coluna de custo do item é unitária ou total da linha antes de multiplicar pela quantidade. O filtro `custo > 0` restringe o relatório à parcela coberta: informe a venda que ficou de fora.
**Prova:** venda do relatório + venda sem custo = venda total do período.
**Leituras típicas:** departamento que pesa mais na venda que na contribuição (gerador de tráfego), queda de margem por mix ou por preço (decomponha: mesma cesta a preços e custos atuais), itens de alto giro com margem abaixo da média do departamento.

### 3.2 Margem negativa

Duas listas diferentes, que não devem ser misturadas:
- **Praticada:** itens cuja venda no período ficou abaixo do custo (preço médio praticado < custo). Colunas: produto, quantidade, preço médio, custo, prejuízo em valor, % das vendas do item em promoção.
- **De cadastro:** itens ativos com preço vigente <= custo atual, vendidos ou não.

Ordene pelo prejuízo em valor. Antes de alarmar, descarte os falsos positivos: custo com erro de embalagem (custo da caixa contra preço da unidade), item em promoção com verba do fornecedor, item de combo com preço rateado.

### 3.3 Custo sem repasse

Itens com aumento de custo nas últimas entradas e preço de venda inalterado.
**Colunas:** produto, custo anterior, custo atual, variação %, data da entrada, preço atual, data da última alteração de preço, margem anterior e atual, preço para recompor a margem anterior (custo atual / (1 - margem anterior)).
Custos por entrada: `../../analyze-mcp-compras/references/relatorios.md`, 3.5. O preço de recomposição é referência de cálculo, não recomendação: elasticidade e concorrência não estão no banco.

### 3.4 Alterações de preço

**Colunas:** data, produto, loja, preço anterior, novo, variação %, usuário, motivo.
**Sintético:** alterações por dia, aumentos x reduções, variação média, itens alterados mais de 3 vezes no período.
Sem tabela de histórico, o ERP não permite este relatório. Não infira alterações a partir do preço praticado na venda (desconto e promoção confundem): diga que o dado não existe.
Usuário é dado pessoal de colaborador: mostre só quando a pergunta for de auditoria.

### 3.5 Resultado de promoção

**Janelas:** antes (mesma duração, imediatamente anterior), durante e depois (mesma duração).
**Colunas por item promovido:** preço normal, preço promocional, desconto %, quantidade por dia nas três janelas, aumento de volume % (durante / antes), venda, contribuição nas três janelas, variação da contribuição.

```sql
SELECT i.<cod_produto>,
       CAST(SUM(CASE WHEN i.<data> <  '2025-07-08' THEN i.<quantidade> ELSE 0 END) / 7.0 AS float) qtd_dia_antes,
       CAST(SUM(CASE WHEN i.<data> >= '2025-07-08' AND i.<data> < '2025-07-15' THEN i.<quantidade> ELSE 0 END) / 7.0 AS float) qtd_dia_durante,
       CAST(SUM(CASE WHEN i.<data> >= '2025-07-15' THEN i.<quantidade> ELSE 0 END) / 7.0 AS float) qtd_dia_depois,
       CAST(SUM(CASE WHEN i.<data> >= '2025-07-08' AND i.<data> < '2025-07-15'
                     THEN i.<valor_liquido> - COALESCE(i.<custo_unitario>, 0) * i.<quantidade> ELSE 0 END) AS float) contrib_durante
FROM <itens_venda> i
WHERE <filtro_validos> AND i.<cod_produto> IN (<itens_da_promocao>)
  AND i.<data> >= '2025-07-01' AND i.<data> < '2025-07-22'
GROUP BY i.<cod_produto>
```

**O que dizer e o que não dizer:**
- O aumento de volume é uma **comparação antes e depois**, não efeito causal: sazonalidade, dia de pagamento, clima e ruptura anterior entram junto. Se houver lojas fora da promoção, use-as como controle e diga isso.
- A queda no "depois" indica antecipação de compra (o cliente estocou).
- Canibalização: mostre a venda dos demais itens da mesma categoria nas três janelas.
- A conta que importa é a contribuição: volume maior com contribuição menor só se justifica por tráfego, e tráfego se mede em cupons, não no item.

### 3.6 Preço de cadastro x praticado

**Colunas:** produto, loja, preço vigente na data, preço unitário do item vendido, diferença, quantidade de ocorrências, operador ou PDV quando a pergunta for de auditoria.
Compare com o preço **vigente na data da venda** (histórico), não com o de hoje. Classifique: desconto registrado, promoção vigente, preço de atacado por quantidade, alteração manual, sem explicação. Só o último grupo é divergência.
