# Fiscal: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.8)

Consultas em SQL Server com marcadores `<assim>`. O sintético por CFOP com participação por janela (3.1) e a conferência cabeçalho x itens (3.3) são **[validado]**: rodaram pelo conector Archeo em banco real. As demais são **[modelo]** até passarem na prova no banco conectado.

## 1. Mapeamento

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Cabeçalho da nota | Totais, situação, numeração | `nota`, `nf`, `nfe`, `nota_header`, `documento_fiscal`, `docto`, `capa` | Chave completa (loja, número, série, modelo, tipo), datas de emissão e de entrada, situação, cancelamento |
| Itens da nota | CFOP, CST, tributos por item | `nota_item`, `nf_item`, `item_nota`, `det` | CFOP por item (pode diferir do cabeçalho), bases, alíquotas, valores |
| Cupom e NFC-e | Venda de caixa | `nfce`, `cupom`, `sat`, `ecf`, `reducao_z` | Se o detalhe está aqui ou só o resumo vai para as notas |
| Parceiro | Cliente e fornecedor do documento | `cliente`, `fornecedor`, `parceiro`, `cnpj`, `uf` | UF (operação interna ou interestadual) |
| CFOP e natureza | Descrição da operação | `cfop`, `natureza_operacao`, `codigo_fiscal` | Cadastro com descrição e se movimenta estoque e financeiro |
| Situação tributária | CST, CSOSN | `cst`, `csosn`, `sit_trib`, `situacao_tributaria` | Formato (2 ou 3 dígitos), por imposto |
| Tributos | Resumo | `icms`, `icms_st`, `subst`, `pis`, `cofins`, `ipi`, `iss`, `fcp`, `difal`, `ibs`, `cbs`, `_is` | Base, alíquota e valor de cada um, no item e no cabeçalho |
| Cadastro tributário do produto | Inconsistências | `ncm`, `cest`, `tributacao`, `figura_fiscal`, `aliquota` | Por produto, por UF ou por loja |
| Eventos e controle | Sequência, inutilização | `inutilizacao`, `evento`, `cancelamento`, `protocolo`, `chave_acesso` | Faixas inutilizadas, protocolo de autorização |

## 2. O que medir

- Notas por tipo (entrada, saída), modelo e situação: contagem e valor.
- Período com dado e volume por mês.
- % de itens com CFOP, CST, NCM, base e alíquota preenchidos.
- Colunas de tributo existentes mas zeradas em todo o histórico (não capturadas).

Para achar as colunas certas numa tabela de nota (costumam ter mais de cem), consulte o catálogo com filtro de nome em vez de descrever a tabela inteira:

```sql
SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = '<nota_item>'
  AND (COLUMN_NAME LIKE '%cfop%' OR COLUMN_NAME LIKE '%cst%' OR COLUMN_NAME LIKE '%icms%'
       OR COLUMN_NAME LIKE '%pis%' OR COLUMN_NAME LIKE '%cofins%' OR COLUMN_NAME LIKE '%val%' OR COLUMN_NAME LIKE '%vlr%')
```

## 3. Relatórios

### 3.1 Documentos fiscais: sintético

**Agrupamentos:** CFOP (default), CST, alíquota de ICMS, modelo, dia, UF, parceiro.
**Colunas:** chave do agrupamento com descrição, documentos, itens, valor contábil, base de ICMS, ICMS, base de ST, ICMS-ST, IPI, PIS, COFINS, isentas, outras, participação %.

```sql
SELECT x.cfop, x.itens, CAST(x.valor AS float) valor,
       CAST(x.icms AS float) icms, CAST(x.icms_st AS float) icms_st,
       CAST(100.0 * x.valor / NULLIF(SUM(x.valor) OVER (), 0) AS float) part_pct
FROM (SELECT i.<cfop> cfop, COUNT(*) itens,
             SUM(COALESCE(i.<valor_total>, 0)) valor,
             SUM(COALESCE(i.<valor_icms>, 0)) icms,
             SUM(COALESCE(i.<valor_icms_st>, 0)) icms_st
      FROM <nota_item> i
      JOIN <nota> h ON h.<cod_loja> = i.<cod_loja> AND h.<num_nota> = i.<num_nota> /* + série, modelo e tipo */
      WHERE h.<situacao_autorizada> AND h.<cod_loja> = <loja>
        AND h.<data> >= '2025-07-01' AND h.<data> < '2025-08-01'
      GROUP BY i.<cfop>) x
ORDER BY x.valor DESC OFFSET 0 ROWS
```

"Isentas" e "outras" dependem do CST: só preencha essas colunas se o banco já as gravar; não as derive por conta própria.
**Prova:** soma do relatório = soma dos itens das notas autorizadas do período; documentos = contagem no cabeçalho.

### 3.2 Documentos fiscais: analítico

**Por produto:** código, descrição, NCM (Nomenclatura Comum do Mercosul), CFOP, CST, quantidade, valor, base, alíquota, ICMS, ST, PIS, COFINS; uma linha por produto + CFOP + CST + alíquota.
**Por nota (conferência):** data, número, série, modelo, parceiro, UF, CFOP, valor de produtos, desconto, frete, total, ICMS, ST, situação, chave de acesso.
Volume alto: sintético e os 30 maiores na conversa, completo em planilha, com filtro obrigatório de período e loja (método comum, seção 5).
**Leituras típicas:** mesmo produto com CST ou alíquota diferentes no período (mudança de cadastro ou erro), CFOP incompatível com a UF do parceiro (interno 5.xxx para outra UF), item tributado com base zero.

### 3.3 Cabeçalho x itens

```sql
SELECT COUNT(*) notas,
       SUM(CASE WHEN i.soma IS NULL THEN 1 ELSE 0 END) sem_item,
       SUM(CASE WHEN ABS(h.<valor_produtos> - COALESCE(i.soma, 0)) > 0.05 THEN 1 ELSE 0 END) divergentes,
       CAST(SUM(h.<valor_produtos>) AS float) total_cabecalho,
       CAST(SUM(COALESCE(i.soma, 0)) AS float) total_itens
FROM <nota> h
LEFT JOIN (SELECT <cod_loja>, <num_nota>, SUM(COALESCE(<valor_total>, 0)) soma
           FROM <nota_item> GROUP BY <cod_loja>, <num_nota>) i
       ON i.<cod_loja> = h.<cod_loja> AND i.<num_nota> = h.<num_nota>
WHERE h.<data> >= '2025-07-01' AND h.<data> < '2025-08-01'
```

**Antes de chamar de divergência**, elimine as causas estruturais, nesta ordem:
1. chave de junção incompleta (falta série, modelo ou tipo, e notas diferentes se misturam);
2. o valor do item é bruto e o do cabeçalho é líquido de desconto, ou o contrário (teste `item - desconto`);
3. frete, despesas e impostos por fora rateados no item;
4. notas canceladas com itens removidos.

Uma taxa de divergência muito alta (dezenas por cento) quase sempre é uma dessas causas, não erro de emissão. Depois de ajustar, liste as divergentes restantes com número, parceiro, os dois valores e a diferença. Tolerância de R$ 0,05 por nota para arredondamento.
**Prova:** notas = fecham + divergentes + sem item.

### 3.4 Entradas x saídas por CFOP

Duas tabelas lado a lado (entradas 1, 2, 3; saídas 5, 6, 7), agrupadas pelo CFOP, com valor contábil, base e ICMS, e os grupos de operação: compra e venda, devolução, transferência, bonificação, remessa e retorno, uso e consumo, baixa de estoque.
**Leituras típicas:** transferências entre lojas que não fecham (saída de uma sem entrada na outra, no mesmo período), devoluções acima do padrão, entradas de uso e consumo classificadas como revenda.

### 3.5 Resumo de tributos

**Colunas por imposto:** base, valor, alíquota efetiva (valor / base), nas saídas (débito) e nas entradas (crédito destacado).
Apresente como **débitos e créditos destacados nos documentos**. A diferença entre os dois **não é o imposto a recolher**: a apuração tem ajustes, estornos, créditos não aproveitáveis, regimes especiais e ST que não estão nos documentos. Diga isso junto do número.
**Prova:** total por imposto = soma por CFOP = soma por alíquota.

### 3.6 Sequência e situação

**Por loja, modelo e série:** primeiro e último número do período, emitidas, canceladas, inutilizadas, denegadas, faltantes.

```sql
SELECT h.<serie>, MIN(h.<num_nota>) primeiro, MAX(h.<num_nota>) ultimo, COUNT(*) registradas,
       MAX(h.<num_nota>) - MIN(h.<num_nota>) + 1 - COUNT(DISTINCT h.<num_nota>) faltantes
FROM <nota> h
WHERE h.<tipo> = <saida_emissao_propria> AND h.<modelo> = <modelo> AND h.<cod_loja> = <loja>
  AND h.<data> >= '2025-07-01' AND h.<data> < '2025-08-01'
GROUP BY h.<serie>
```

Para listar os números faltantes, use `LEAD(num) OVER (PARTITION BY serie ORDER BY num)` e mostre os intervalos onde `próximo - atual > 1`. Só vale para **emissão própria**: notas de terceiros não têm sequência. Antes de reportar salto, desconte as faixas inutilizadas e veja se a numeração é compartilhada entre lojas ou PDVs.
**Canceladas:** quantidade, valor, % sobre as emitidas, prazo entre emissão e cancelamento, e por usuário quando a pergunta for de auditoria.

### 3.7 Cadastro tributário

Exceções, cada uma com contagem e amostra, priorizadas pela venda do produto:
- produto ativo sem NCM, ou com NCM de tamanho diferente de 8 dígitos;
- produto com ST sem CEST (Código Especificador da Substituição Tributária);
- mesmo NCM com tributações diferentes entre produtos (pode ser legítimo; é lista de revisão);
- CST que indica tributação com alíquota zero, ou CST de isenção com alíquota preenchida;
- produto vendido no período com tributação diferente da do cadastro atual.

Apresente como **itens a revisar pelo fiscal**. A skill não diz qual é a tributação correta.

### 3.8 Campos da reforma tributária

Mede o preenchimento, não o valor: por mês e por modelo, % de itens com CST e classificação tributária de IBS e CBS preenchidos, % com base e valor, e a mesma coisa para IS. Liste os produtos de maior venda sem classificação.
Só existe se o banco tiver as colunas. Sem elas, diga que a versão do ERP ainda não as traz.
