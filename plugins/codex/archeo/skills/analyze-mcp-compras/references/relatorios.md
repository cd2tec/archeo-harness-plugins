# Compras e abastecimento: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.7)

Consultas em SQL Server com marcadores `<assim>`; **[modelo]** até passarem na prova no banco conectado.

## 1. Mapeamento

Saldo, movimento, produto e venda por item: `../../analyze-mcp-estoque/references/relatorios.md`, seção 1. Acrescente:

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Pedido de compra | Pendentes, nível de serviço | `pedido_compra`, `ped_compra`, `ordem_compra`, `oc`, `purchase` | Cabeçalho e itens; datas de emissão e de entrega prevista; situação; quantidade pedida, recebida e cancelada |
| Entrada (recebimento) | Custo, prazo, pedido x nota | `nota_entrada`, `nf_entrada`, `recebimento`, `entrada`, `compra` | Data de emissão x data de entrada; tipo de operação (compra, bonificação, devolução, transferência); vínculo com o pedido |
| Fornecedor | Quebras | `fornecedor`, `parceiro`, `pessoa` | Chave, situação, comprador responsável |
| Produto x fornecedor | Embalagem, prazo | `prod_fornec`, `fornecedor_produto`, `embalagem`, `fator`, `lead_time`, `prazo_entrega` | Fator de conversão, múltiplo de compra, fornecedor principal |
| Parâmetros de reposição | Sugestão | `estoque_minimo`, `estoque_maximo`, `ponto_pedido`, `dias_cobertura`, `frequencia` | Se estão preenchidos de verdade (mínimo zerado em tudo = não usado) |
| Custo | Variação | `custo`, `custo_ultima_entrada`, `custo_medio`, `preco_compra` | Composição do custo e histórico de alteração |

## 2. O que medir

- Pedidos: por situação, período, % com data de entrega prevista, % de itens com quantidade recebida preenchida.
- Entradas: por tipo de operação, % com vínculo ao pedido, diferença entre data de emissão e de entrada.
- Parâmetros de reposição: % de itens ativos com mínimo, máximo, prazo e embalagem preenchidos.

## 3. Relatórios

### 3.1 ABC de abastecimento

**Colunas:** posição, código, descrição, fornecedor principal, quantidade vendida, venda a custo (ou quantidade, conforme a dimensão), participação %, acumulado %, classe, saldo atual, dias de cobertura, pendente de recebimento, alerta.

**Alertas do cruzamento:**
| Classe | Cobertura | Alerta |
|---|---|---|
| A | Menos de 7 dias e sem pedido pendente | Risco de ruptura em item crítico |
| A | Saldo <= 0 | Ruptura em item crítico |
| C | Mais de 90 dias | Excesso em item de baixa relevância |
| Qualquer | Saldo > 0 e sem venda | Parado (ver `analyze-mcp-estoque`, 3.5) |

A curva segue o modelo de `../../analyze-mcp-vendas/references/relatorios.md`, 3.1, trocando a medida por `SUM(quantidade * custo)` ou `SUM(quantidade)`, com `LEFT JOIN` no saldo e no pendente por produto. Limites de cobertura são defaults: ajuste por departamento quando o usuário indicar.

**Por quantidade ou por valor:** por valor responde "onde está o capital"; por quantidade responde "o que mais movimenta doca e gôndola". Itens A nas duas são o núcleo do abastecimento.
**Prova:** soma da medida = total do período; número de itens antes e depois do cruzamento é o mesmo (join com saldo não pode multiplicar nem descartar linhas).

### 3.2 Sugestão de compra

**Fórmula (por produto e local):**

```
demanda_dia    = quantidade vendida no período / dias considerados
dias_alvo      = lead time + intervalo entre pedidos + dias de segurança
necessidade    = demanda_dia x dias_alvo
sugestão bruta = necessidade - saldo disponível - pendente de recebimento
sugestão       = arredonda para cima no múltiplo da embalagem de compra (zero se negativa)
```

**Colunas:** código, descrição, embalagem, demanda diária, saldo, pendente, cobertura atual em dias, dias alvo, necessidade, sugestão em unidades e em embalagens, custo unitário, valor da sugestão, observação.

```sql
SELECT p.<cod_produto>, p.<descricao>,
       CAST(COALESCE(v.qtd, 0) / 90.0 AS float) demanda_dia,
       CAST(COALESCE(s.<saldo>, 0) AS float) saldo,
       CAST(COALESCE(pe.pendente, 0) AS float) pendente,
       CAST(COALESCE(v.qtd, 0) / 90.0 * <dias_alvo>
            - COALESCE(s.<saldo>, 0) - COALESCE(pe.pendente, 0) AS float) sugestao_bruta,
       CAST(pf.<fator_embalagem> AS float) embalagem, CAST(p.<custo> AS float) custo
FROM <produto> p
JOIN <produto_fornecedor> pf ON pf.<cod_produto> = p.<cod_produto> AND pf.<cod_fornecedor> = <fornecedor>
LEFT JOIN <saldo_estoque> s ON s.<cod_produto> = p.<cod_produto> AND s.<cod_loja> = <loja>
LEFT JOIN (SELECT i.<cod_produto>, SUM(i.<quantidade>) qtd
           FROM <itens_venda> i
           WHERE <filtro_validos> AND i.<cod_loja> = <loja>
             AND i.<data> >= '2025-07-01' AND i.<data> < '2025-09-29'
           GROUP BY i.<cod_produto>) v ON v.<cod_produto> = p.<cod_produto>
LEFT JOIN (SELECT pi.<cod_produto>,
                  SUM(pi.<qtd_pedida> - COALESCE(pi.<qtd_recebida>, 0) - COALESCE(pi.<qtd_cancelada>, 0)) pendente
           FROM <pedido_compra_item> pi
           JOIN <pedido_compra> pc ON pc.<num_pedido> = pi.<num_pedido>
           WHERE pc.<cod_loja> = <loja> AND pc.<situacao> IN (<abertos>)
           GROUP BY pi.<cod_produto>) pe ON pe.<cod_produto> = p.<cod_produto>
WHERE p.<ativo> = <sim>
```

Faça o arredondamento por embalagem e o corte em zero no resultado (ou com `CEILING` na consulta), e marque na coluna de observação:
- item com ruptura no período (demanda subestimada);
- item novo, com menos de 30 dias de venda (demanda instável);
- item com promoção no período (demanda superestimada);
- saldo negativo (tratado como zero; corrija o estoque antes);
- item sem embalagem ou sem custo.

**Premissas a declarar sempre:** de onde vieram lead time, intervalo e segurança (cadastro, observado ou default informado pelo usuário). Sem nenhuma dessas fontes, pergunte os três números em uma pergunta só.
**Limite:** média simples não trata sazonalidade nem tendência. Para datas sazonais (Páscoa, Natal, volta às aulas), compare com o mesmo período do ano anterior e diga que a sugestão não captura o pico.
**Prova:** para 5 itens da amostra, confira demanda, saldo e pendente contra as fontes; valor total = soma das linhas.

### 3.3 Pedidos pendentes

**Colunas:** pedido, fornecedor, emissão, entrega prevista, dias de atraso, produto, pedido, recebido, cancelado, pendente, valor pendente.
**Sintético por fornecedor:** pedidos, itens pendentes, valor pendente, valor atrasado, maior atraso.
**Faixas de atraso:** no prazo, 1 a 7, 8 a 15, 16 a 30, acima de 30 dias. Pedido muito antigo em aberto geralmente é sujeira (saldo que deveria ter sido eliminado): destaque em vez de somar ao que "vai chegar".
**Prova:** pedido = recebido + cancelado + pendente em cada item.

### 3.4 Nível de serviço do fornecedor

| Indicador | Fórmula |
|---|---|
| Atendimento em quantidade (fill rate) | Quantidade recebida / quantidade pedida, nos pedidos com entrega prevista no período |
| Pontualidade | Recebimentos até a data prevista / recebimentos |
| OTIF (On Time In Full; no prazo e completo) | Pedidos recebidos completos e no prazo / pedidos |
| Prazo médio observado | Média de (data de entrada - data do pedido), em dias |
| Variabilidade do prazo | Desvio padrão do prazo (é ela que define o estoque de segurança) |

**Colunas:** fornecedor, pedidos, valor comprado, atendimento %, pontualidade %, OTIF %, prazo médio, desvio do prazo.
Sem data de entrega prevista, não há pontualidade nem OTIF: entregue atendimento e prazo observado e diga o que faltou.
**Prova:** recebimentos considerados = entradas de compra do período com vínculo a pedido; informe o % de entradas sem pedido (compra fora do processo).

### 3.5 Variação de custo de compra

**Colunas:** produto, fornecedor, custo da penúltima entrada, custo da última entrada, variação %, data, quantidade comprada, impacto estimado (variação x quantidade vendida mensal), preço de venda atual, margem antes e depois.

Compare entradas de **compra** (sem bonificação, devolução ou transferência) do mesmo fornecedor e da mesma embalagem. Para pegar as duas últimas entradas por produto, use `ROW_NUMBER() OVER (PARTITION BY produto ORDER BY data DESC, chave DESC)` em tabela derivada e filtre `rn <= 2`.
**Leituras típicas:** aumento ainda não repassado ao preço (margem comprimida, cruze com `analyze-mcp-precos`), variação grande por mudança de embalagem ou de composição de imposto (falso aumento), queda de custo não aproveitada.

### 3.6 Pedido x nota

**Colunas:** pedido, nota, produto, quantidade pedida x faturada, custo pedido x faturado, diferença em valor, tipo de divergência (preço maior, quantidade maior, item sem pedido, item não entregue).
**Tolerância default:** 1% no preço e na quantidade, ajustável. Declare.
**Prova:** valor da nota = soma dos itens conferidos + itens sem pedido.

### 3.7 Concentração de fornecedores

ABC de fornecedores por valor comprado; participação do maior, dos 5 e dos 10 maiores; por departamento, itens da classe A de venda com fornecedor único. Leitura de risco de dependência, não de desempenho.
