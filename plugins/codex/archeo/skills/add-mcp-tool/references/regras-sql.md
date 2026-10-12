# Regras de SQL para ferramentas do Archeo MCP Creator

Vale para qualquer banco conectado ao Archeo. Escreva os parâmetros sempre como `$1`, `$2`, ... independentemente da engine: é a sintaxe do MCP Creator. O resto do SQL segue o dialeto da engine informada por `db_connection_status`.

Marcação de confiança: **[validado]** foi confirmado contra um banco real pelo conector Archeo; **[hipótese]** é sintaxe padrão da engine, ainda não exercitada pelo conector. Em hipóteses, o passo de validação é o que decide.

## 1. Sintaxe por engine

| Necessidade | SQL Server [validado] | PostgreSQL [hipótese] | Oracle [hipótese] | MySQL/MariaDB [hipótese] |
|---|---|---|---|---|
| Parâmetro date | `CAST($1 AS date)` | `CAST($1 AS date)` | `TO_DATE($1, 'YYYY-MM-DD')` se chegar como texto; testar | `CAST($1 AS date)` |
| Parâmetro timestamp | `CAST($1 AS datetime2)` | `CAST($1 AS timestamp)` | `TO_TIMESTAMP($1, 'YYYY-MM-DD HH24:MI:SS')` | `CAST($1 AS datetime)` |
| Concatenar texto | `'%' + $1 + '%'` | `'%' \|\| $1 \|\| '%'` | `'%' \|\| $1 \|\| '%'` | `CONCAT('%', $1, '%')` |
| Ano e mês | `YEAR(c)`, `MONTH(c)` | `EXTRACT(YEAR FROM c)` | `EXTRACT(YEAR FROM c)` | `YEAR(c)`, `MONTH(c)` |
| Hora do dia | `DATEPART(hour, c)` | `EXTRACT(HOUR FROM c)` | `TO_NUMBER(TO_CHAR(c, 'HH24'))` | `HOUR(c)` |
| Nulo para zero | `COALESCE(c, 0)` | `COALESCE(c, 0)` | `COALESCE(c, 0)` | `COALESCE(c, 0)` |
| Ordenação | `ORDER BY ... OFFSET 0 ROWS` (ajuste, seção 4) | `ORDER BY` simples; testar | `ORDER BY` simples; testar | `ORDER BY` simples; testar |

Sistemas legados costumam guardar data e hora como número ou texto (`AAAAMMDD`, `HHMM`, `HHMMSS`). Confirme o formato olhando dados reais na exploração antes de escrever filtros ou agrupamentos, e não confie só no nome da coluna nem no manual do sistema: views podem mudar o formato do campo bruto.

## 2. Parâmetros

### Tipo na tela x cast no SQL

| Dado | Tipo na tela | Observação |
|---|---|---|
| Data de período | `date` | O tipo vira contrato: o modelo recebe validação de formato e o servidor recusa lixo antes do SQL |
| Data e hora exata | `timestamp` | Só quando a hora tem função na consulta |
| Código numérico (loja, filial, produto) | `integer` | `number` aceitaria `1.5` |
| Valor monetário, percentual | `number` | |
| Flag liga/desliga | `boolean` | [hipótese] o formato do binding não foi testado; valide com os dois valores |
| GUID | `uuid` | |
| Texto ou código alfanumérico | `string` | Inclusive códigos numéricos guardados como texto com zeros à esquerda |

Mantenha o cast no SQL mesmo com o tipo certo na tela: não se sabe se o conector faz o binding como tipo nativo ou como texto. No primeiro caso o cast é redundante; no segundo, evita interpretação de data conforme o idioma ou NLS da sessão.

Atenção a códigos que são número na tabela de movimento e texto no cadastro (ou o contrário): o join precisa converter os dois lados para o mesmo tipo, e o tipo do parâmetro segue a coluna filtrada.

### Datas: intervalo semiaberto

Use `coluna >= <cast de $1> AND coluna < <cast de $2>`, com fim **exclusivo**, e diga isso na descrição (ex.: "para julho inteiro use 2025-07-01 e 2025-08-01"). Evita perder o último dia quando a coluna tem hora e evita `BETWEEN` com `23:59:59`. Não aplique função sobre a coluna filtrada (`TRUNC(c)`, `CAST(c AS date)`): mata o índice.

### Filtro opcional ("todos")

Não está garantido que parâmetro opcional chegue como NULL. Use um **sentinela** e trate NULL junto, usando o parâmetro uma única vez:

```sql
AND coluna = COALESCE(NULLIF($3, 0), coluna)      -- inteiro: 0 = todos
AND coluna = COALESCE(NULLIF($3, ''), coluna)     -- texto: vazio = todos
```

Evite `CASE WHEN $3 = 0 THEN coluna ELSE $3 END`: repete o parâmetro e, se `$3` vier NULL, retorna **zero linhas sem erro**, a pior falha possível. Se a coluna filtrada aceitar NULL, o padrão acima exclui as linhas nulas no modo "todos"; nesse caso use `($3 = 0 OR coluna = $3)` e valide.

Registre o sentinela na descrição (`$3 = código da loja, 0 = todas`).

### Obrigatório

- Datas de período: **obrigatórias**. Período aberto em base de produção vira full scan e estoura o timeout.
- Filtros com sentinela: podem ficar obrigatórios (o modelo manda o sentinela) ou opcionais, desde que o SQL use o padrão acima.

### O que parâmetro não faz

Nome de tabela, coluna, schema, direção de ordenação, lista dinâmica de `IN`. Para lista de códigos, use parâmetros fixos com sentinela (`$3`, `$4`, `$5`) ou uma ferramenta por recorte.

## 3. Diagnóstico quando a validação falha

O conector pode devolver erro genérico (`TOOL_EXECUTION_FAILED`) sem a mensagem do banco. Não tente às cegas; bisseccione:

1. Rode **sem `ORDER BY`** e **sem `WITH`**. Se passar, aplique o ajuste correspondente da seção 4.
2. Se falhar, rode só `COUNT(*)` com o `WHERE`. Se passar, o problema está nas colunas do SELECT: provavelmente um tipo que o conector não serializa (decimal, datetime, binário, LOB). Aplique cast coluna a coluna.
3. Se o `WHERE` sozinho falhar, teste os literais um a um (formato de data, tipo do código, cast).
4. Registre na ficha qual sintoma apareceu e qual contorno foi usado.

## 4. Ajustes de compatibilidade a verificar

Comportamentos que podem aparecer conforme a engine e a versão do conector. Verifique cada sintoma no passo de validação e aplique o ajuste só quando ele aparecer.

1. **Consulta com `ORDER BY` falha.** Alguns bancos (SQL Server, por exemplo) não aceitam `ORDER BY` quando a consulta é encapsulada para aplicar o limite de linhas. Ajuste: `ORDER BY ... OFFSET 0 ROWS`.
2. **Valores `decimal`/`numeric` chegam codificados** (texto em base64 em vez de número). Ajuste: `CAST(ROUND(expr, 2) AS float)`. Se a precisão exata importar mais que o tipo numérico, converta para texto com 2 casas.
3. **Erro sem a mensagem do banco.** Use o diagnóstico da seção 3.
3a. **Consulta com `WITH` (CTE) falha.** O encapsulamento que limita linhas não aceita CTE. Ajuste: reescreva com tabelas derivadas (`FROM (SELECT ...) x`).
3b. **Join com cadastro multiplica valores.** Cadastros com uma linha por loja (finalizadoras, departamentos, produtos) repetem cada movimento uma vez por loja. Ajuste: junte pelo código **e pela loja** (o mesmo código pode significar outra coisa em outra loja), com um segundo join só pelo código como fallback, e confira se a soma bate com o total sem join.
4. **Descrição de tabela ou view indisponível.** Alternativa: consultar o catálogo pela ferramenta de query (`INFORMATION_SCHEMA.COLUMNS` em SQL Server, PostgreSQL e MySQL; `ALL_TAB_COLUMNS` em Oracle).
5. **Saída grande demais** em tabelas largas. Selecione só as colunas necessárias em vez de amostrar a tabela inteira.

## 5. Checklist antes de entregar

- [ ] A ficha cita o banco, a engine e o conector usados.
- [ ] Um único SELECT, sem `;` final, sem escrita, sem identificador vindo de parâmetro.
- [ ] Parâmetros numerados em sequência a partir de `$1`, sem lacuna, na mesma ordem da tabela de parâmetros.
- [ ] Cada `$n` usado uma vez sempre que possível.
- [ ] Datas com cast e intervalo semiaberto, sem função sobre a coluna filtrada.
- [ ] Filtros "todos" com sentinela documentado na descrição.
- [ ] Somas compostas com `COALESCE(campo, 0)` (NULL anula a expressão inteira sem erro).
- [ ] Filtros fixos de cancelamento, exclusão lógica ou status aplicados e explicados na descrição.
- [ ] Ajustes de compatibilidade aplicados quando o sintoma apareceu.
- [ ] SQL executado com literais em pelo menos dois cenários; números do teste incluídos na ficha.
- [ ] Teto de linhas compatível com o pior caso do agrupamento.
