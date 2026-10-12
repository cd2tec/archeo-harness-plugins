# Formato do config do painel

`scripts/build_dashboard.py` lê este JSON, valida e injeta no template. Campos com `?` são opcionais.

```json
{
  "titulo": "Painel Rede Exemplo",
  "rede": "Rede Exemplo · 3 lojas",
  "fonte": { "banco": "erp_varejo", "engine": "SQL Server 16", "conector": "Archeo Manager" },
  "geradoEm": "2026-10-11T09:30:00-03:00",
  "modo": "snapshot",
  "live?": { "server": "Archeo Manager", "tool": "db_..._db_read_only_query", "schema": "dbo", "refetchMs": 300000 },
  "metaSecao": "kpis",
  "secoes": [ ... ],
  "leitura?": [ { "nivel": "atencao", "titulo": "...", "texto": "..." } ],
  "leituraEm?": "2026-10-11T09:30:00-03:00",
  "indisponiveis?": [ { "titulo": "Margem bruta", "motivo": "custo uniforme de 30% em todos os departamentos, provavelmente estimado" } ]
}
```

- `metaSecao`: id da seção cuja primeira linha traz `periodo_ini`, `periodo_fim`, `anterior_ini`, `anterior_fim` (texto `AAAA-MM-DD`). Alternativa: `"meta": { "sql?": "...", "dados?": [ {...} ] }`.
- `modo`: `snapshot` exige `dados` em toda seção; `live` exige `sql` em toda seção e proíbe `dados`.
- Todas as seções aceitam `id`, `tipo`, `titulo`, `nota?` (texto curto no canto), `vazio?` (texto quando não há linhas), `sql?`, `dados?`, `formato?` (`moeda`, `inteiro`, `decimal`, `pct`, `dias`).

## Tipos de seção

### `kpis` (faixa do topo)

```json
{ "id": "kpis", "tipo": "kpis", "titulo": "Totalizadores", "campoComparavel": "comparavel",
  "cards": [
    { "campo": "venda_liquida", "anterior": "venda_liquida_ant", "rotulo": "Venda líquida", "formato": "moeda", "melhor": "alta" },
    { "campo": "margem_pct", "rotulo": "Margem bruta", "formato": "pct", "nota": "custo estimado" }
  ],
  "dados": [ { "venda_liquida": 51159.2, "venda_liquida_ant": 105.65, "comparavel": 0, "periodo_ini": "2025-07-01", "...": "..." } ] }
```

`melhor`: `alta`, `baixa` ou `neutra` (define a cor da variação). `ocultarSemDado: true` esconde o card quando o campo vier nulo.

### `score` (faixa do topo, ao lado dos totalizadores)

```json
{ "id": "score", "tipo": "score", "titulo": "Índice de saúde",
  "componentes": [ { "campo": "desconto_pct", "rotulo": "Desconto", "peso": 15, "ruim": 8, "bom": 2, "formato": "pct" } ],
  "dados": [ { "desconto_pct": 4.99 } ] }
```

### `linha`

```json
{ "id": "dia", "tipo": "linha", "titulo": "Venda por dia", "formato": "moeda", "preencherDias": true,
  "series": { "atual": "Jul a ago/2025", "anterior": "Mai a jun/2025" },
  "dados": [ { "x": "2025-07-31", "atual": 33657.01, "anterior": 43.42 } ] }
```

### `heatmap`

```json
{ "id": "horario", "tipo": "heatmap", "titulo": "Venda por dia da semana e hora", "largura": "metade", "formato": "moeda",
  "dados": [ { "dia": 5, "hora": 21, "valor": 4923.07 } ] }
```

`dia`: 1 = domingo ... 7 = sábado. Cores em 5 faixas por quantil.

### `barras`

```json
{ "id": "deptos", "tipo": "barras", "titulo": "Departamentos", "largura": "metade", "formato": "moeda", "participacao": true,
  "dados": [ { "rotulo": "Açougue", "valor": 5597.26, "var_pct": -3.2 } ] }
```

`participacao: true` mostra a fatia de cada barra no total exibido. `var_pct` opcional mostra a variação; `melhor: "baixa"` inverte a cor.

### `tabela`

```json
{ "id": "operadores", "tipo": "tabela", "titulo": "Operadores", "largura": "inteira",
  "colunas": [ { "campo": "operador", "rotulo": "Operador" }, { "campo": "desconto_pct", "rotulo": "Desconto", "formato": "pct" } ],
  "dados": [ { "operador": "Operador 9", "desconto_pct": 8.38 } ] }
```

Colunas sem `formato` são texto; com `formato`, números alinhados à direita.

## Largura

`largura`: `inteira` (padrão), `metade`, `terco`, `dois-tercos`. Em telas estreitas tudo vira uma coluna. Componha linhas que fechem 12 colunas (duas metades, um terço com dois terços) para não sobrar buraco.
