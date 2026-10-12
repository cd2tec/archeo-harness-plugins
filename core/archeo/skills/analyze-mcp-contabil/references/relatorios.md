# Contábil: mapeamento, relatórios e consultas-modelo

Conteúdo:
1. Mapeamento
2. O que medir
3. Relatórios (3.1 a 3.7)

Consultas em SQL Server com marcadores `<assim>`; **[modelo]** até passarem na prova no banco conectado. Estão escritas para o formato "uma linha por conta, com indicador D ou C"; adapte para os outros formatos (SKILL.md, item 1).

## 1. Mapeamento

| Domínio | Para quê | Termos de busca | O que confirmar |
|---|---|---|---|
| Lançamento | Tudo | `lancamento`, `lancto`, `lcto`, `partida`, `movimento_contabil`, `ctb`, `razao`, `journal` | Formato da partida, data de competência, valor, histórico, lote, origem, situação |
| Plano de contas | Hierarquia, natureza | `plano_conta`, `conta_contabil`, `conta`, `pc`, `chart` | Código, código reduzido, descrição, analítica ou sintética, natureza, conta pai ou máscara |
| Saldo | Saldo anterior | `saldo_conta`, `saldo_mensal`, `saldo_contabil`, `fechamento` | Período de cada saldo, se é acumulado |
| Centro de custo | Quebra | `centro_custo`, `ccusto`, `cc`, `centro_resultado` | % dos lançamentos de resultado preenchidos |
| Histórico padrão | Leitura | `historico`, `hist_padrao` | Código e complemento |
| Origem e lote | Integração | `lote`, `origem`, `modulo`, `integracao`, `documento` | Quais módulos integram e com que frequência |
| LALUR | Adições e exclusões | `lalur`, `lacs`, `adicao`, `exclusao`, `parte_a`, `parte_b`, `prejuizo_fiscal` | Se existe e está em uso (tabela vazia é o caso mais comum) |

## 2. O que medir

- Lançamentos por mês e por origem; primeira e última data; por situação.
- Débitos e créditos totais por mês (já mostra onde não fecha).
- Contas analíticas com movimento, contas sem movimento no exercício, lançamentos em conta sintética.
- Identificação dos lançamentos de encerramento e de abertura.

## 3. Relatórios

### 3.1 Balancete de verificação

**Colunas:** código, descrição, saldo anterior (D ou C), débitos, créditos, saldo atual (D ou C). Contas sintéticas totalizando as filhas, no nível pedido.

```sql
SELECT pc.<codigo>, pc.<descricao>, pc.<natureza>,
       CAST(SUM(CASE WHEN l.<data> <  '2025-07-01' THEN <deb> - <cre> ELSE 0 END) AS float) saldo_anterior,
       CAST(SUM(CASE WHEN l.<data> >= '2025-07-01' THEN <deb> ELSE 0 END) AS float) debitos,
       CAST(SUM(CASE WHEN l.<data> >= '2025-07-01' THEN <cre> ELSE 0 END) AS float) creditos,
       CAST(SUM(<deb> - <cre>) AS float) saldo_atual
FROM <lancamento> l
JOIN <plano_contas> pc ON pc.<conta> = l.<conta>
WHERE l.<empresa> = <empresa> AND <lancamento_efetivado>
  AND l.<data> >= '2025-01-01' AND l.<data> < '2025-08-01'
GROUP BY pc.<codigo>, pc.<descricao>, pc.<natureza>
HAVING SUM(<deb>) <> 0 OR SUM(<cre>) <> 0
ORDER BY pc.<codigo> OFFSET 0 ROWS
```

Onde `<deb>` = `CASE WHEN l.<dc> = 'D' THEN l.<valor> ELSE 0 END` e `<cre>` o equivalente para crédito. Saldo positivo = devedor, negativo = credor; converta para D ou C na apresentação.

- O exemplo acumula do início do exercício. Para contas patrimoniais, o saldo anterior correto vem de **toda** a história ou da tabela de saldos: prefira a tabela de saldos e some o movimento do período.
- **Nível sintético:** com máscara no código, agrupe por `LEFT(codigo, n)` do nível desejado e traga a descrição da conta sintética; com coluna de conta pai, suba um nível por join (um join por nível, sem CTE recursiva).
- Conta com saldo invertido à natureza (caixa credor, fornecedor devedor) é achado: liste.

**Prova:** soma de débitos = soma de créditos; soma dos saldos (com sinal) = zero; equação patrimonial.

### 3.2 Razão

**Colunas:** data, lote ou número do lançamento, histórico, contrapartida, débito, crédito, saldo após o lançamento (D ou C). Linha inicial com o saldo anterior.

```sql
SELECT CONVERT(varchar(10), r.dia, 23) data, r.num, r.historico,
       CAST(r.deb AS float) debito, CAST(r.cre AS float) credito,
       CAST(r.saldo_anterior + SUM(r.deb - r.cre) OVER (ORDER BY r.dia, r.num, r.seq ROWS UNBOUNDED PRECEDING) AS float) saldo
FROM (SELECT l.<data> dia, l.<num_lancamento> num, l.<sequencia> seq, l.<historico> historico,
             <deb> deb, <cre> cre,
             (SELECT COALESCE(SUM(<deb_a> - <cre_a>), 0) FROM <lancamento> a
              WHERE a.<empresa> = l.<empresa> AND a.<conta> = l.<conta> AND a.<data> < '2025-07-01') saldo_anterior
      FROM <lancamento> l
      WHERE l.<empresa> = <empresa> AND l.<conta> = <conta> AND <lancamento_efetivado>
        AND l.<data> >= '2025-07-01' AND l.<data> < '2025-08-01') r
ORDER BY r.dia, r.num, r.seq OFFSET 0 ROWS
```

Contrapartida: no formato de uma linha por conta, é a outra conta do mesmo lançamento; com várias, mostre "diversas". Razão é por conta: sem conta informada, mostre as 20 contas com maior movimento para o usuário escolher.
**Prova:** saldo final = saldo da conta no balancete da mesma data.

### 3.3 Diário

**Colunas:** data, número do lançamento, conta, descrição, histórico, débito, crédito; total por lançamento e por dia.
Volume alto por natureza: exija período curto (até um mês) e empresa, entregue em planilha, e traga na conversa só os totais por dia e os lançamentos acima de um valor de corte.
**Prova:** débito = crédito em cada lançamento.

### 3.4 Resultado gerencial

Estrutura a partir dos grupos do plano: receita bruta, deduções, receita líquida, custo da mercadoria vendida, lucro bruto, despesas por grupo, resultado operacional, resultado financeiro, resultado antes dos impostos.
**Colunas:** linha, mês, mês anterior, acumulado do exercício, % sobre a receita líquida (análise vertical), variação % (horizontal).
- O mapeamento conta para linha vem do plano (grupos de resultado). Se a estrutura não for evidente, mostre os grupos encontrados e confirme com o usuário antes de montar.
- Exclua os lançamentos de encerramento.
- Chame de **gerencial**: a demonstração oficial tem regras de apresentação próprias.
- Por loja ou centro de custo só se o preenchimento for alto; informe a parcela sem centro.

**Prova:** resultado = soma das contas de resultado no balancete do mesmo período.

### 3.5 Integridade dos lançamentos

Exceções, cada uma com contagem, valor e amostra:
- lançamento ou lote em que débito diferente de crédito;
- dia ou mês que não fecha (mostre o primeiro período em que a diferença aparece);
- lançamento em conta sintética ou em conta inativa;
- conta de resultado sem centro de custo, quando a empresa usa;
- lançamento sem histórico, ou com histórico genérico;
- lançamentos manuais (origem diferente de integração) em contas que deveriam ser só integradas (estoque, fornecedores, clientes);
- valores redondos altos, lançamentos em fim de semana ou no último dia do mês com estorno no primeiro dia do seguinte;
- lançamentos duplicados (mesma data, contas, valor e histórico).

```sql
SELECT l.<num_lancamento>, CONVERT(varchar(10), MIN(l.<data>), 23) data,
       CAST(SUM(<deb>) AS float) debitos, CAST(SUM(<cre>) AS float) creditos,
       CAST(SUM(<deb> - <cre>) AS float) diferenca
FROM <lancamento> l
WHERE l.<empresa> = <empresa> AND l.<data> >= '2025-07-01' AND l.<data> < '2025-08-01'
GROUP BY l.<num_lancamento>
HAVING ABS(SUM(<deb> - <cre>)) > 0.005
ORDER BY ABS(SUM(<deb> - <cre>)) DESC OFFSET 0 ROWS
```

São indícios para revisão, não conclusões: lançamento manual de ajuste no fechamento pode ser legítimo.

### 3.6 Conciliação módulo x contábil

| Módulo | Posição do módulo | Conta contábil |
|---|---|---|
| Estoque | Valor do estoque a custo na data | Estoques de mercadorias |
| Contas a receber | Títulos em aberto na data | Clientes, cartões a receber |
| Contas a pagar | Títulos em aberto na data | Fornecedores |
| Bancos | Saldo das contas correntes | Bancos conta movimento |

**Colunas:** módulo, posição do módulo, saldo contábil, diferença, % e explicação.
A posição do módulo precisa ser **na mesma data** do saldo contábil: estoque em data passada vem de `analyze-mcp-estoque` (posição retroativa); títulos em aberto em data passada, de `analyze-mcp-financeiro` (emitidos até a data e baixados depois dela). Comparar posição de hoje com saldo do fechamento é o erro que mais gera diferença falsa.
Peça ao usuário quais contas correspondem a cada módulo se o plano não deixar claro.

### 3.7 Posição do LALUR

Só existe se o ERP controlar a Parte A (adições, exclusões e compensações ao lucro líquido) e a Parte B (saldos a controlar para exercícios futuros: prejuízos fiscais, diferenças temporárias).
**Colunas, Parte A:** período, lucro líquido antes dos tributos, adições por natureza, exclusões por natureza, lucro real antes da compensação, compensação de prejuízo, lucro real.
**Parte B:** conta, saldo inicial, movimentação, saldo final.
Na maioria dos ERPs de varejo isso fica no sistema fiscal ou do escritório contábil e as tabelas estão vazias: diga isso e pare, sem tentar reconstruir o LALUR a partir dos lançamentos. Classificar o que é adição ou exclusão é juízo tributário, não consulta.
