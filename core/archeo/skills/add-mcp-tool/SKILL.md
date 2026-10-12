---
name: add-mcp-tool
description: Gera, pronta para copiar e colar, a ficha de cadastro de uma nova ferramenta no Archeo MCP Creator (tela "Nova ferramenta") para qualquer banco conectado ao Archeo: nome técnico, nome de exibição, descrição, schema, SQL com parâmetros posicionais $1..$n, tipo e obrigatoriedade de cada parâmetro, limites por chamada e valores de teste. Sempre explora e valida o SQL no banco conectado na sessão antes de entregar. Use quando o usuário quiser criar, cadastrar ou publicar uma ferramenta no Archeo ou no MCP Creator, transformar uma consulta em tool do Archeo, perguntar "gere o SQL para cadastrar como ferramenta" ou "quais tipos uso nos parâmetros", mesmo sem citar o nome da skill.
---

# add-mcp-tool: ficha de cadastro de ferramenta no Archeo MCP Creator

O Archeo MCP Creator expõe bancos legados para IA. Uma **ferramenta** é um SELECT fixo com parâmetros de valor, validado pelo servidor antes de ser aceito. Esta skill entrega tudo que o usuário precisa para preencher a tela "Nova ferramenta" de primeira, com um SQL que já rodou no banco conectado.

A skill funciona para qualquer banco e qualquer domínio. Ela não depende de conhecimento prévio da base: o conhecimento vem da exploração do banco conectado no momento e do que o usuário disser.

Quem chama a ferramenta depois é outro modelo de IA, que só enxerga o nome técnico, a descrição e o schema dos parâmetros. Descrição e tipos são o contrato, tão importantes quanto o SQL.

## A tela que será preenchida

| Campo | O que é |
|---|---|
| Nome técnico | Identificador da ferramenta para o modelo |
| Nome de exibição | Rótulo humano na interface |
| Descrição | Campo de uma linha; é o que o modelo lê para decidir quando e como chamar |
| Schema | Dropdown (ex.: `dbo`, `public`). Tabelas sem prefixo são salvas como `schema.tabela` |
| SQL | Somente um SELECT. Parâmetros posicionais: `$1`, `$2`, ... |
| Parâmetros | Para cada `$n`: nome, tipo (`string`, `integer`, `number`, `boolean`, `date`, `timestamp`, `uuid`) e checkbox "Obrigatório" |
| Limites por chamada | Linhas (padrão 500), Bytes (padrão 1000000), Timeout em ms (padrão 5000) |

O validador do servidor recusa **identificadores livres, múltiplas instruções e qualquer escrita**. Parâmetro só substitui valor, nunca tabela, coluna, schema ou direção de ORDER BY.

## Fluxo

### 1. Identifique o banco conectado

As ferramentas de um conector Archeo seguem o padrão `mcp__<servidor Archeo>__db_<nome do banco>_<engine>_<id>__<ação>`, com ações como `db_connection_status`, `db_list_tables`, `db_search_columns`, `db_describe_table`, `db_sample_table` e `db_read_only_query`. Podem estar deferidas: procure com ToolSearch (ex.: "db_read_only_query", "Archeo") e carregue as do conector em uma chamada só.

- **Um conector:** use-o.
- **Vários:** pergunte ao usuário em qual banco a ferramenta será cadastrada, a menos que o pedido já deixe claro. A ficha vale para um banco só.
- **Nenhum:** diga que não há banco do Archeo conectado nesta sessão e que a ficha precisa dele para ser gerada e validada. Ofereça seguir sem validação apenas se o usuário fornecer a estrutura das tabelas, e marque a ficha como **não validada**.

Rode `db_connection_status` e registre **engine e versão**: a sintaxe muda por engine (`references/regras-sql.md`, seção 1).

### 2. Entenda a pergunta de negócio

Qual pergunta a ferramenta responde, qual a granularidade de cada linha (por dia, por loja, por produto) e quais filtros viram parâmetro. Se a conversa já tem uma consulta pronta, parta dela. Pergunte só o que mudar o SQL; o resto, assuma e declare na ficha.

### 3. Explore o banco conectado

Descubra o modelo a partir do próprio banco, não de suposição:

- **Localize os dados:** `db_search_columns` com termos de negócio prováveis (venda, valor, data, loja, cliente, status), em português e inglês e em abreviações comuns de sistemas legados (`vlr`, `dta`, `cod`, `qtd`, `flg`). `db_list_tables` para ver views prontas: views de resumo costumam já carregar regras de negócio e devem ser preferidas a tabelas cruas.
- **Entenda a estrutura:** `db_describe_table` nas candidatas (tipos, nulidade).
- **Veja dados reais:** `db_sample_table` ou um SELECT com poucas linhas, selecionando só as colunas necessárias (tabelas largas estouram a saída).
- **Meça antes de prometer:** `COUNT(*)`, `MIN`/`MAX` da coluna de data, percentual de nulos nas colunas de valor, valores distintos de colunas de status/flag. Isso revela período com dado real, colunas zeradas e flags de cancelamento ou exclusão lógica.
- **Regras implícitas:** colunas como `flg_*`, `status`, `cancelado`, `excluido`, `ativo`, `dt_exclusao` quase sempre precisam de filtro fixo. Quando não der para inferir o significado com segurança (qual coluna é o valor líquido, qual status conta como venda), pergunte ao usuário em vez de adivinhar, e registre a decisão na descrição.

### 4. Escreva o SQL no formato Archeo

Siga `references/regras-sql.md`: tipos e casts por engine, intervalo de datas, filtros opcionais com sentinela, e ajustes de compatibilidade do conector.

### 5. Valide no banco conectado

Execute pela ferramenta de query somente leitura, trocando cada `$n` por um literal do tipo certo e mantendo o resto do texto idêntico ao que será cadastrado, inclusive `ORDER BY` e paginação. Teste pelo menos dois cenários: o filtro "todos" (sentinela) e um filtro específico. Confira se os números fazem sentido com o que a exploração mostrou.

Se falhar, siga o diagnóstico em `references/regras-sql.md`, seção 3. Não entregue SQL que não rodou sem dizer isso com destaque.

### 6. Entregue a ficha

Use o formato abaixo, para o usuário copiar campo a campo.

## Formato da entrega

```
**Banco:** <nome do banco> (<engine e versão>), via <servidor Archeo>

**Campos do formulário**
| Campo | Valor |
| Nome técnico | `...` |
| Nome de exibição | `...` |
| Schema | `...` |
| Descrição | `...` |

**SQL**
(bloco sql pronto para colar)

**Parâmetros**
| Posição | Nome | Tipo | Obrigatório | Exemplo |

**Limites**
| Linhas | Bytes | Timeout (ms) |  + uma frase se fugir do padrão

**Teste após salvar**
Valores para cada $n e o resultado esperado (números reais da validação).

**Premissas e pontos de atenção**
Regras de negócio assumidas, ajustes de compatibilidade usados, riscos de performance, dados indisponíveis.
```

### Nome técnico

`snake_case`, sem acento, padrão `<sistema>_<assunto>_<recorte>`, com o sistema derivado do nome do banco conectado: `pdv_venda_resumo_loja_mes`, `erp_estoque_produto_loja`, `fin_titulos_vencidos_cliente`. O prefixo evita colisão quando o mesmo agente tem vários bancos conectados.

### Nome de exibição

Curto, em português, sem jargão: `Venda por loja e mês`.

### Descrição

Escreva para o modelo que vai chamar a ferramenta, em um parágrafo:
- o que retorna (colunas principais e granularidade da linha);
- filtros fixos embutidos e fórmulas relevantes;
- o significado de cada `$n`, com formato e exemplo;
- convenções: datas com fim exclusivo, sentinela de "todos" (ex.: `0 = todas as lojas`);
- como agregar o resultado se o usuário pedir total.

### Limites

- **Linhas:** dimensione pelo pior caso do agrupamento (lojas x meses, horas x dias). Listas de registros precisam de filtro obrigatório ou paginação por parâmetro, não de limite maior.
- **Timeout:** 5000 ms para agregações sobre período filtrado. Suba para 15000 ms se a consulta varre muitos anos, tabelas grandes ou colunas sem índice, e diga isso.
- **Bytes:** o padrão basta, exceto com colunas de texto longo.

## Exemplo

`references/exemplo-ficha.md` mostra uma ficha completa sobre um banco fictício de varejo em SQL Server. Use como referência de nível de detalhe e formato, não como fonte de regras para outros bancos.
