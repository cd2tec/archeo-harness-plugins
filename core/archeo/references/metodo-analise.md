# Método comum das skills `analyze-mcp-*`

Todas as skills de análise do plugin (`analyze-mcp-estoque`, `-vendas`, `-compras`, `-precos`, `-perdas`, `-fiscal`, `-contabil`, `-financeiro`) seguem este método. Cada skill acrescenta o catálogo de relatórios, o mapeamento e as provas do seu domínio em `references/relatorios.md`.

Conteúdo:
1. Princípios
2. Fluxo
3. Regras de consulta
4. Formato da entrega
5. Volume e exportação
6. Dados pessoais
7. Depois do relatório: ferramenta ou painel
8. Checklist

## 1. Princípios

- **O banco decide, não o manual.** Os nomes de relatório vêm do vocabulário dos ERPs de varejo, mas tabelas, colunas e regras saem da exploração do banco conectado. Nenhum nome de tabela nas consultas-modelo é real: são marcadores `<assim>`.
- **Relatório sem prova não sai.** Cada relatório do catálogo tem uma prova de reconciliação (saldo inicial + movimento = saldo final, débito = crédito, soma das partes = total). Prova que não fecha vira o primeiro item da entrega, não uma nota de rodapé.
- **Dado ruim aparece.** Campo nunca preenchido, custo zerado, posição desatualizada e base sem movimento são achados. Diga o que faltou e o que isso impede de concluir.
- **Só leitura.** Toda consulta usa as ferramentas somente leitura do conector. Nada é gravado no ERP.
- **Não é documento oficial.** Relatórios fiscais e contábeis daqui servem para conferência e gestão. Livros, obrigações acessórias e apurações oficiais saem do ERP ou do sistema fiscal, com responsável técnico.

## 2. Fluxo

### 2.1 Identifique o banco conectado

Como em `../skills/add-mcp-tool/SKILL.md`, passo 1: ferramentas `mcp__<conector>__db_<banco>_<engine>_<id>__<ação>` (`db_connection_status`, `db_list_tables`, `db_search_columns`, `db_describe_table`, `db_sample_table`, `db_read_only_query`), possivelmente deferidas (ToolSearch, uma chamada só). Com vários bancos, pergunte qual; sem nenhum, diga que a análise precisa de um banco do Archeo conectado e pare.

Rode `db_connection_status`, anote engine e versão e leia `../skills/add-mcp-tool/references/regras-sql.md` (seções 1, 3 e 4) antes da primeira consulta.

### 2.2 Feche o escopo

Todo relatório tem quatro eixos. Use o default da skill quando o usuário não disser, e declare o recorte na entrega.

| Eixo | Pergunta | Default geral |
|---|---|---|
| Unidade | Qual empresa, loja ou depósito? | Todas, com quebra por loja quando houver mais de uma |
| Tempo | Período de movimento ou data de posição? | Últimos 30 dias até a **última data com movimento** (não até hoje: réplicas e bases de laboratório param de receber dado) |
| Recorte | Departamento, fornecedor, cliente, conta? | Sem filtro |
| Nível | Sintético ou analítico? | Sintético, com o analítico dos 20 maiores |

Pergunte só o que muda o resultado. Um pedido vago ("me dá o estoque") recebe o relatório padrão da skill com o recorte declarado, não uma entrevista.

### 2.3 Mapeie o domínio

Use a tabela de mapeamento da skill: termos de busca por domínio, em português, inglês e abreviações de legado (`vlr`, `dta`, `cod`, `qtd`, `flg`, `sld`). Prefira views de resumo do próprio sistema. Se `db_describe_table` falhar, consulte o catálogo (`INFORMATION_SCHEMA.COLUMNS`, ou `ALL_TAB_COLUMNS` em Oracle) filtrando a tabela e padrões de coluna, nunca sem `WHERE`.

### 2.4 Meça antes de calcular

Para cada tabela que entra no relatório: `COUNT(*)`, `MIN` e `MAX` da data, percentual de nulos nas colunas de valor e valores distintos das colunas de status, tipo e flag. É aqui que aparecem:

- tabela vazia ou parada no tempo (o módulo não é usado, ou o dado vive em outro lugar);
- tipos de movimento e de documento que precisam virar filtro fixo ou sinal (entrada, saída, estorno);
- registros cancelados, estornados, de teste ou excluídos logicamente;
- cadastros com uma linha por loja, que multiplicam o join.

Quando o significado de um código não for inferível com segurança (qual tipo é devolução, qual situação é "em aberto"), **pergunte ao usuário** e registre a decisão nas premissas.

### 2.5 Calcule e prove

Monte a consulta a partir do modelo da skill, rode e aplique a prova do relatório. Diferença acima da tolerância indicada (2% quando não houver outra) pede investigação antes de entregar: join que multiplica, filtro fixo faltando, sinal invertido, unidade de medida diferente.

### 2.6 Leia

De 3 a 5 achados, do mais urgente ao menos, cada um com o número que o sustenta e o que fazer com ele. Leitura de negócio, não descrição da tabela. Inclua sempre um item sobre qualidade do dado quando 2.4 ou 2.5 mostraram algo.

## 3. Regras de consulta

Valem as de `regras-sql.md` e as de `../skills/add-mcp-dashboard/references/indicadores-varejo.md`, seção 2. As que mais pesam em relatório:

- **Sem CTE**: use tabelas derivadas (`FROM (SELECT ...) x`).
- **`ORDER BY` com `OFFSET 0 ROWS`** no SQL Server; teste nas outras engines.
- **`CAST(... AS float)`** em valores quando o conector devolver decimal codificado.
- **Funções de janela funcionam** pelo conector em SQL Server (**[validado]**: `SUM(...) OVER ()` para participação e `SUM(...) OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING)` para acumulado, dentro de tabela derivada). Use para saldo acumulado, participação e classes ABC. Sempre desempate a ordenação com a chave, senão o acumulado muda entre execuções.
- **Datas com fim exclusivo**, sem função sobre a coluna filtrada.
- **Agregue no banco.** Não traga milhares de linhas para somar na conversa.
- **Sinal explícito.** Movimentos costumam guardar quantidade sempre positiva e o sentido em uma coluna de tipo. Converta com `CASE` e nunca presuma o sinal.

As consultas-modelo das skills estão em SQL Server. Marcação: **[validado]** quando o padrão rodou pelo conector em banco real; **[modelo]** quando é o desenho de referência, que só vale depois do passo 2.5 no banco do usuário.

## 4. Formato da entrega

```
**<Nome do relatório>**
Banco: <banco> (<engine e versão>), via <conector>
Recorte: <unidade> | <período ou data de posição> | <filtros> | <nível>

**Resumo**
3 a 6 totais em uma linha ou tabela curta.

**Relatório**
Tabela com as colunas do catálogo. Até 30 linhas na conversa; o restante vai em arquivo (seção 5).

**Leitura**
1. ... (número, o que significa, o que fazer)

**Prova**
O que foi reconciliado, o resultado e a diferença.

**Premissas e qualidade do dado**
Filtros fixos aplicados, significados assumidos, campos indisponíveis, relatórios pedidos que não puderam ser gerados e por quê.
```

Números em formato brasileiro (`1.234,56`), moeda com `R$`, percentual com uma casa. Datas `dd/mm/aaaa`. Código e descrição lado a lado sempre que houver cadastro.

## 5. Volume e exportação

- **Sintético na conversa, analítico em arquivo.** Acima de 30 linhas, entregue planilha (`.xlsx` ou `.csv`) com uma aba de dados, uma de resumo e uma de premissas. Use a skill de planilha da sessão, se houver.
- **Analítico grande não se pagina pela conversa.** Um Kardex de todos os produtos ou um razão de todas as contas tem centenas de milhares de linhas. Entregue o sintético, o analítico dos maiores e ofereça a ferramenta parametrizada (seção 7) para o usuário consultar item a item.
- O conector limita linhas por chamada. Para exportar algo entre o limite e ~20 mil linhas, pagine por faixa de chave (`WHERE chave > <última>` com `TOP`), nunca por `OFFSET` crescente, e confira a contagem final contra `COUNT(*)`.

## 6. Dados pessoais

Relatórios por cliente, fornecedor pessoa física, operador ou vendedor trazem dado pessoal (LGPD, Lei Geral de Proteção de Dados). Por padrão:

- agregue ou use o código interno; mostre nome só quando o relatório precisar dele para ser útil;
- mascare CPF (`***.123.456-**`); CNPJ pode aparecer;
- não exporte cadastro (endereço, telefone, e-mail) junto com relatório de venda ou de cobrança, a menos que o usuário peça com finalidade clara.

## 7. Depois do relatório: ferramenta ou painel

Um relatório que o usuário vai pedir de novo deve virar ativo, não conversa:

- **Ferramenta no MCP Creator:** cada relatório do catálogo lista os parâmetros naturais. Ofereça `add-mcp-tool` para gerar a ficha com o SQL já validado nesta sessão.
- **Painel:** indicadores recorrentes cabem em `add-mcp-dashboard`.

Ofereça em uma linha no fim da entrega, sem insistir.

## 8. Checklist

- [ ] Banco, engine, conector e recorte declarados.
- [ ] Tabelas medidas (volume, período, flags) antes do cálculo.
- [ ] Filtros fixos de cancelamento, estorno e exclusão lógica aplicados e listados.
- [ ] Prova do relatório executada, com a diferença informada.
- [ ] Joins com cadastro por loja conferidos (soma com join = soma sem join).
- [ ] Posição de estoque, saldo ou título com a data de referência explícita.
- [ ] Leitura com número e ação, incluindo qualidade do dado.
- [ ] Dado pessoal agregado ou mascarado.
- [ ] Relatório fiscal ou contábil marcado como conferência.
- [ ] Indisponíveis listados com o motivo.
